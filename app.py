from flask import Flask, render_template, request, jsonify
import os
import secrets
import threading
import time
import traceback
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from services.gemini_service import suggest_hashtags, add_tags_to_content
from services.publisher_service import publish_to_both
from dotenv import load_dotenv
from models import db, PostHistory
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

# 用于取消发布的事件
CANCEL_EVENTS = {}
CANCEL_EVENTS_LOCK = threading.Lock()

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
        # 检查是否已取消
        with CANCEL_EVENTS_LOCK:
            cancel_event = CANCEL_EVENTS.get(job_id)
        if cancel_event and cancel_event.is_set():
            return
        _job_append(job_id, message)

    # 创建取消事件
    cancel_event = threading.Event()
    with CANCEL_EVENTS_LOCK:
        CANCEL_EVENTS[job_id] = cancel_event

    try:
        progress('开始发布任务')
        
        # 检查是否已取消
        if cancel_event.is_set():
            _job_update(
                job_id,
                status='cancelled',
                success=False,
                message='发布已被用户取消'
            )
            return
            
        abs_paths = []
        image_urls = []
        for p in image_paths or []:
            if not p:
                continue
            clean = p.replace('\\', '/').lstrip('/')
            abs_paths.append(os.path.join(app.root_path, clean))
            if clean.startswith('static/'):
                image_urls.append('/' + clean)
        
        results = publish_to_both(content, platforms, image_paths=abs_paths, progress=progress, cancel_event=cancel_event)
        
        # 检查是否被取消
        if cancel_event.is_set():
            _job_update(
                job_id,
                status='cancelled',
                success=False,
                message='发布已被用户取消'
            )
            return
            
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
    except Exception as e:
        if cancel_event.is_set():
            _job_update(
                job_id,
                status='cancelled',
                success=False,
                message='发布已被用户取消'
            )
        else:
            traceback.print_exc()
            _job_update(
                job_id,
                status='error',
                success=False,
                message=f'发布失败: {str(e)}'
            )
    finally:
        # 清理取消事件
        with CANCEL_EVENTS_LOCK:
            if job_id in CANCEL_EVENTS:
                del CANCEL_EVENTS[job_id]

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
    try:
        data = request.get_json()
        content = data.get('content', '')
        
        if not content:
            return jsonify({'success': False, 'message': '内容不能为空'})
        
        refined = add_tags_to_content(content)
        
        if not refined:
            return jsonify({'success': False, 'message': 'AI 服务返回空内容'})
        
        return jsonify({'success': True, 'content': refined})
    except Exception as e:
        print(f"API refine 错误: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'服务器错误: {str(e)}'})

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
    try:
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
            resize_image_if_needed(save_path, max_size=2048)
            rel_path = os.path.join('static', 'uploads', filename)
            url = '/' + rel_path.replace('\\', '/')
            results.append({
                'id': file_id,
                'url': url,
                'path': rel_path.replace('\\', '/')
            })
            print(f"图片上传成功: {filename}, URL: {url}")

        if not results:
            return jsonify({'success': False, 'message': '图片上传失败', 'errors': errors})

        return jsonify({'success': True, 'images': results, 'errors': errors if errors else None})
    except Exception as e:
        print(f"上传错误: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'上传失败: {str(e)}'})

@app.route('/api/publish/status/<job_id>')
def api_publish_status(job_id):
    _cleanup_jobs()
    with PUBLISH_LOCK:
        job = PUBLISH_JOBS.get(job_id)
        if not job:
            return jsonify({'success': False, 'message': '任务不存在'})
        return jsonify({'success': True, 'job': job})

@app.route('/api/publish/cancel/<job_id>', methods=['POST'])
def api_cancel_publish(job_id):
    """取消正在进行的发布任务"""
    with CANCEL_EVENTS_LOCK:
        cancel_event = CANCEL_EVENTS.get(job_id)
        if cancel_event:
            cancel_event.set()
            return jsonify({'success': True, 'message': '正在取消发布...'})
    
    with PUBLISH_LOCK:
        job = PUBLISH_JOBS.get(job_id)
        if job and job['status'] in ('done', 'error', 'cancelled'):
            return jsonify({'success': False, 'message': '任务已完成或已取消'})
    
    return jsonify({'success': False, 'message': '任务不存在或已结束'})

@app.route('/history')
def history_page():
    return render_template('history.html', active_page='history')

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

if __name__ == '__main__':
    app.run(debug=True, port=5000, use_reloader=False)
