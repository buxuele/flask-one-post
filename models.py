from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class PostHistory(db.Model):
    __tablename__ = 'post_history'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    platforms = db.Column(db.String(100), nullable=False)
    twitter_success = db.Column(db.Boolean, default=False)
    zhihu_success = db.Column(db.Boolean, default=False)
    image_paths = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'platforms': self.platforms,
            'twitter_success': self.twitter_success,
            'zhihu_success': self.zhihu_success,
            'image_paths': self.image_paths.split(',') if self.image_paths else [],
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }

class ScheduledPost(db.Model):
    __tablename__ = 'scheduled_post'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    platforms = db.Column(db.String(100), nullable=False)
    image_paths = db.Column(db.Text, default='')
    scheduled_at = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, published, failed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.now)
    published_at = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'platforms': self.platforms,
            'image_paths': self.image_paths.split(',') if self.image_paths else [],
            'scheduled_at': self.scheduled_at.strftime('%Y-%m-%d %H:%M'),
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M'),
            'published_at': self.published_at.strftime('%Y-%m-%d %H:%M') if self.published_at else None,
            'error_message': self.error_message
        }
