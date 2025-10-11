from datetime import datetime
from enum import Enum
from src.database import db

class ConfigType(Enum):
    """Configuration type enumeration"""
    APPLICATION = 'application'
    INFRASTRUCTURE = 'infrastructure'

class Configuration(db.Model):
    """Configuration model for storing app and infrastructure configs"""
    __tablename__ = 'configurations'
    
    id = db.Column(db.Integer, primary_key=True)
    app_name = db.Column(db.String(100), nullable=False, index=True)
    config_type = db.Column(db.Enum(ConfigType), nullable=False, index=True)
    environment = db.Column(db.String(50), nullable=False, index=True)  # dev/staging/prod
    key = db.Column(db.String(200), nullable=False, index=True)
    value = db.Column(db.Text, nullable=False)  # Store as text, can be JSON
    description = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint on app_name + environment + key combination
    __table_args__ = (
        db.UniqueConstraint('app_name', 'environment', 'key', name='unique_config_per_app_env_key'),
    )
    
    def to_dict(self):
        """Convert configuration to dictionary"""
        return {
            'id': self.id,
            'app_name': self.app_name,
            'config_type': self.config_type.value if self.config_type else None,
            'environment': self.environment,
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'created_by': self.creator.username if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Configuration {self.app_name}:{self.environment}:{self.key}>'
