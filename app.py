from flask import Flask, render_template, request, jsonify
import os
import threading
import time
import traceback
import uuid
from werkzeug.utils import secure_filename
from services.gemini_service import suggest_hashtags, refine_content
from services.publisher_service import publish_to_both
from dotenv import load_dotenv
from models import db, PostHistory

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

INITIAL_IMAGES = []
PUBLISH_JOBS = {}
PUBLISH_LOCK = threading.Lock()
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

@app.route('/api/upload', methods=['POST'])
def api_upload():
    files = request.files.getlist('images')
    if not files:
        return jsonify({'success': False, 'message': '未找到图片文件'})

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    results = []

    for f in files:
        if not f or not f.filename:
            continue
        safe_name = secure_filename(f.filename)
        if not safe_name:
            continue
        file_id = uuid.uuid4().hex
        filename = f'{file_id}_{safe_name}'
        save_path = os.path.join(UPLOAD_DIR, filename)
        f.save(save_path)
        rel_path = os.path.join('static', 'uploads', filename)
        url = '/' + rel_path.replace('\\', '/')
        results.append({
            'id': file_id,
            'url': url,
            'path': rel_path.replace('\\', '/')
        })

    if not results:
        return jsonify({'success': False, 'message': '图片保存失败'})

    return jsonify({'success': True, 'images': results})

@app.route('/api/publish/status/<job_id>')
def api_publish_status(job_id):
    with PUBLISH_LOCK:
        job = PUBLISH_JOBS.get(job_id)
        if not job:
            return jsonify({'success': False, 'message': '任务不存在'})
        return jsonify({'success': True, 'job': job})

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

if __name__ == '__main__':
    app.run(debug=True, port=5000, use_reloader=False)
