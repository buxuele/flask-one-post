from flask import Flask, render_template, request, jsonify
import os
import secrets
import threading
import time
import traceback
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from services.gemini_service import suggest_hashtags, refine_content
from services.publisher_service import publish_to_both
from dotenv import load_dotenv
from models import db, PostHistory, ScheduledPost
from PIL import Image
import io

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') or secrets.token_hex(32)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

INITIAL_IMAGES = []
PUBLISH_JOBS = {}
PUBLISH_LOCK = threading.Lock()
JOB_MAX_AGE = 600  # 已完成的 job 保留10分钟
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'static', 'uploads')

def _now_label():
    return time.strftime('%H:%M:%S')

def _job_append(job_id, message):
    with PUBLISH_LOCK:
        job = PUBLISH_JOBS.get(job_id)
        if not job:
            return
        job['steps'].append({'time': _now_label(), 'message': message})

def _job_update(job_id, **fields):
    with PUBLISH_LOCK:
        job = PUBLISH_JOBS.get(job_id)
        if not job:
            return
        job.update(fields)
        if fields.get('status') in ('done', 'error'):
            job['finished_at'] = time.time()

def _cleanup_jobs():
    """清理过期的已完成 job"""
    now = time.time()
    with PUBLISH_LOCK:
        expired = [
            jid for jid, j in PUBLISH_JOBS.items()
            if j.get('finished_at') and now - j['finished_at'] > JOB_MAX_AGE
        ]
        for jid in expired:
            del PUBLISH_JOBS[jid]

def _run_publish_job(job_id, content, platforms, image_paths):
    def progress(message):
        _job_append(job_id, message)

    try:
        progress('开始发布任务')
        abs_paths = []
        image_urls = []
        for p in image_paths or []:
            if not p:
                continue
            clean = p.replace('\\', '/').lstrip('/')
            abs_paths.append(os.path.join(app.root_path, clean))
            if clean.startswith('static/'):
                image_urls.append('/' + clean)
        results = publish_to_both(content, platforms, image_paths=abs_paths, progress=progress)
        success = results['twitter'] or results['zhihu']
        message = ' | '.join(results['messages'])

        with app.app_context():
            history = PostHistory(
                content=content,
                platforms=','.join(platforms),
                twitter_success=results['twitter'],
                zhihu_success=results['zhihu'],
                image_paths=','.join(image_urls)
            )
            db.session.add(history)
            db.session.commit()

        _job_update(
            job_id,
            status='done',
            success=success,
            message=message,
            results=results
        )
    except Exception:
        traceback.print_exc()
        _job_update(
            job_id,
            status='error',
            success=False,
            message='发布失败，请查看控制台日志'
        )

@app.route('/')
def index():
    return render_template('index.html', images=INITIAL_IMAGES, active_page='publish')

@app.route('/api/suggest-hashtags', methods=['POST'])
def api_suggest_hashtags():
    data = request.get_json()
    content = data.get('content', '')
    tags = suggest_hashtags(content)
    return jsonify({'hashtags': tags})

@app.route('/api/refine', methods=['POST'])
def api_refine():
    data = request.get_json()
    content = data.get('content', '')
    refined = refine_content(content)
    return jsonify({'content': refined})

@app.route('/api/publish', methods=['POST'])
def api_publish():
    data = request.get_json()
    content = data.get('content', '')
    platforms = data.get('platforms', ['twitter', 'zhihu'])
    image_paths = data.get('image_paths', [])
    
    if not content:
        return jsonify({'success': False, 'message': '内容不能为空'})
    
    job_id = uuid.uuid4().hex
    with PUBLISH_LOCK:
        PUBLISH_JOBS[job_id] = {
            'status': 'running',
            'success': False,
            'message': '',
            'steps': [{'time': _now_label(), 'message': '任务已创建，准备开始'}]
        }

    thread = threading.Thread(
        target=_run_publish_job,
        args=(job_id, content, platforms, image_paths),
        daemon=True
    )
    thread.start()

    return jsonify({'success': True, 'job_id': job_id})

def resize_image_if_needed(image_path, max_size=1080):
    """Resize image if any dimension exceeds max_size"""
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            if width > max_size or height > max_size:
                ratio = min(max_size / width, max_size / height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                if img.mode in ('RGBA', 'P'):
                    resized = resized.convert('RGB')
                resized.save(image_path, quality=90, optimize=True)
                return True
    except Exception as e:
        print(f"Resize error: {e}")
    return False

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/upload', methods=['POST'])
def api_upload():
    files = request.files.getlist('images')
    if not files:
        return jsonify({'success': False, 'message': '未找到图片文件'})

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    results = []
    errors = []

    for f in files:
        if not f or not f.filename:
            continue
            
        if not allowed_file(f.filename):
            errors.append(f'{f.filename}: 不支持的文件格式')
            continue
            
        f.seek(0, 2)
        file_size = f.tell()
        f.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            errors.append(f'{f.filename}: 文件大小超过20MB限制')
            continue
            
        safe_name = secure_filename(f.filename)
        if not safe_name:
            continue
        file_id = uuid.uuid4().hex
        filename = f'{file_id}_{safe_name}'
        save_path = os.path.join(UPLOAD_DIR, filename)
        f.save(save_path)
        resize_image_if_needed(save_path, max_size=1080)
        rel_path = os.path.join('static', 'uploads', filename)
        url = '/' + rel_path.replace('\\', '/')
        results.append({
            'id': file_id,
            'url': url,
            'path': rel_path.replace('\\', '/')
        })

    if not results:
        return jsonify({'success': False, 'message': '图片上传失败', 'errors': errors})

    return jsonify({'success': True, 'images': results, 'errors': errors if errors else None})

@app.route('/api/publish/status/<job_id>')
def api_publish_status(job_id):
    _cleanup_jobs()
    with PUBLISH_LOCK:
        job = PUBLISH_JOBS.get(job_id)
        if not job:
            return jsonify({'success': False, 'message': '任务不存在'})
        return jsonify({'success': True, 'job': job})

@app.route('/history')
def history_page():
    return render_template('history.html', active_page='history')

@app.route('/about')
def about_page():
    return render_template('about.html', active_page='about')

@app.route('/scheduled')
def scheduled_page():
    return render_template('scheduled.html', active_page='scheduled')

@app.route('/api/history')
def api_history():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    posts = PostHistory.query.order_by(PostHistory.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'posts': [post.to_dict() for post in posts.items],
        'total': posts.total,
        'pages': posts.pages,
        'current_page': page
    })

@app.route('/api/history/<int:post_id>', methods=['DELETE'])
def api_delete_history(post_id):
    post = PostHistory.query.get(post_id)
    if not post:
        return jsonify({'success': False, 'message': '记录不存在'})
    
    db.session.delete(post)
    db.session.commit()
    return jsonify({'success': True, 'message': '删除成功'})

@app.route('/api/history/clear', methods=['POST'])
def api_clear_history():
    try:
        PostHistory.query.delete()
        db.session.commit()
        return jsonify({'success': True, 'message': '清空成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/history/batch-delete', methods=['POST'])
def api_batch_delete_history():
    data = request.get_json()
    ids = data.get('ids', [])
    
    if not ids:
        return jsonify({'success': False, 'message': '未提供要删除的ID'})
    
    try:
        PostHistory.query.filter(PostHistory.id.in_(ids)).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({'success': True, 'message': f'成功删除 {len(ids)} 条记录'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

# 定时发布相关API
@app.route('/api/scheduled', methods=['POST'])
def api_schedule_post():
    data = request.get_json()
    content = data.get('content', '')
    platforms = data.get('platforms', [])
    image_paths = data.get('image_paths', [])
    scheduled_at = data.get('scheduled_at', '')
    
    if not content:
        return jsonify({'success': False, 'message': '内容不能为空'})
    
    if not platforms:
        return jsonify({'success': False, 'message': '请至少选择一个平台'})
    
    if not scheduled_at:
        return jsonify({'success': False, 'message': '请选择发布时间'})
    
    try:
        scheduled_time = datetime.fromisoformat(scheduled_at)
        if scheduled_time <= datetime.now():
            return jsonify({'success': False, 'message': '发布时间必须晚于当前时间'})
    except:
        return jsonify({'success': False, 'message': '无效的时间格式'})
    
    try:
        scheduled = ScheduledPost(
            content=content,
            platforms=','.join(platforms),
            image_paths=','.join(image_paths),
            scheduled_at=scheduled_time
        )
        db.session.add(scheduled)
        db.session.commit()
        return jsonify({'success': True, 'id': scheduled.id, 'message': '定时发布已创建'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/scheduled')
def api_list_scheduled():
    status = request.args.get('status', 'pending')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = ScheduledPost.query
    if status != 'all':
        query = query.filter_by(status=status)
    
    posts = query.order_by(ScheduledPost.scheduled_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'posts': [post.to_dict() for post in posts.items],
        'total': posts.total,
        'pages': posts.pages,
        'current_page': page
    })

@app.route('/api/scheduled/<int:post_id>', methods=['DELETE'])
def api_cancel_scheduled(post_id):
    post = ScheduledPost.query.get(post_id)
    if not post:
        return jsonify({'success': False, 'message': '排期不存在'})
    
    if post.status != 'pending':
        return jsonify({'success': False, 'message': '只能取消待发布的排期'})
    
    try:
        post.status = 'cancelled'
        db.session.commit()
        return jsonify({'success': True, 'message': '已取消'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

# 定时发布调度器
def run_scheduler():
    while True:
        try:
            with app.app_context():
                now = datetime.now()
                due_posts = ScheduledPost.query.filter(
                    ScheduledPost.status == 'pending',
                    ScheduledPost.scheduled_at <= now
                ).all()
                
                for post in due_posts:
                    try:
                        def progress(msg):
                            print(f"[Scheduled {post.id}] {msg}")
                        
                        image_paths = post.image_paths.split(',') if post.image_paths else []
                        platforms = post.platforms.split(',')
                        
                        results = publish_to_both(
                            post.content, 
                            platforms, 
                            image_paths=image_paths, 
                            progress=progress
                        )
                        
                        post.status = 'published'
                        post.published_at = datetime.now()
                        
                        # 添加到历史记录
                        history = PostHistory(
                            content=post.content,
                            platforms=post.platforms,
                            twitter_success=results.get('twitter', False),
                            zhihu_success=results.get('zhihu', False),
                            image_paths=post.image_paths
                        )
                        db.session.add(history)
                        db.session.commit()
                        
                        print(f"[Scheduled {post.id}] Published successfully")
                        
                    except Exception as e:
                        print(f"[Scheduled {post.id}] Error: {e}")
                        post.status = 'failed'
                        post.error_message = str(e)
                        db.session.commit()
                        
        except Exception as e:
            print(f"[Scheduler] Error: {e}")
            
        time.sleep(30)  # 每30秒检查一次

# 启动调度器
scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()

if __name__ == '__main__':
    app.run(debug=True, port=5000, use_reloader=False)
