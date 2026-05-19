from app import db
import os

def normalize_path(file_path):
    """标准化文件路径，移除工作目录前缀"""
    workspace_path = "/home/zwy/project2721707-302151"
    if file_path.startswith(workspace_path):
        return file_path[len(workspace_path):].lstrip('/')
    return file_path


class GlobalVariable(db.Model):
    __tablename__ = 'GlobalVariables'
    
    # 联合主键：name + file_path
    name = db.Column(db.String, primary_key=True)
    file_path = db.Column(db.String, primary_key=True)
    type = db.Column(db.String)
    line_number = db.Column(db.Integer, nullable=False)
    is_static = db.Column(db.Integer, nullable=False, default=0)
    definition_code = db.Column(db.String)
    
    @classmethod
    def find_by_name_and_file(cls, name, file_path):
        """根据名称和标准化的文件路径查找变量"""
        normalized_path = normalize_path(file_path)
        return cls.query.filter_by(
            name=name,
            file_path=normalized_path
        ).first()
    
    def __init__(self, *args, **kwargs):
        if 'file_path' in kwargs:
            kwargs['file_path'] = normalize_path(kwargs['file_path'])
        super().__init__(*args, **kwargs)
    
    def to_dict(self):
        return {
            'name': self.name,
            'file_path': self.file_path,
            'type': self.type,
            'line_number': self.line_number,
            'is_static': bool(self.is_static),
            'definition_code': self.definition_code
        }


class Function(db.Model):
    __tablename__ = 'Functions'
    
    # 联合主键：name + file_path
    name = db.Column(db.String, primary_key=True)
    file_path = db.Column(db.String, primary_key=True)
    return_type = db.Column(db.String)
    parameters = db.Column(db.String)
    start_line = db.Column(db.Integer, nullable=False)
    start_col = db.Column(db.Integer, nullable=False)
    end_line = db.Column(db.Integer, nullable=False)
    end_col = db.Column(db.Integer, nullable=False)
    is_static = db.Column(db.Integer, nullable=False, default=0)
    definition_code = db.Column(db.String)
    
    def __init__(self, *args, **kwargs):
        if 'file_path' in kwargs:
            kwargs['file_path'] = normalize_path(kwargs['file_path'])
        super().__init__(*args, **kwargs)
    
    def to_dict(self):
        return {
            'name': self.name,
            'file_path': self.file_path,
            'return_type': self.return_type,
            'parameters': self.parameters,
            'start_line': self.start_line,
            'start_col': self.start_col,
            'end_line': self.end_line,
            'end_col': self.end_col,
            'is_static': bool(self.is_static),
            'definition_code': self.definition_code
        }


class AccessRelation(db.Model):
    __tablename__ = 'AccessRelations'
    
    # 复合主键（保持不变）
    var_name = db.Column(db.String, primary_key=True)
    func_name = db.Column(db.String, primary_key=True)
    access_type = db.Column(db.String, primary_key=True)
    access_file_path = db.Column(db.String, primary_key=True)
    access_line_number = db.Column(db.Integer, primary_key=True)
    
    def __init__(self, *args, **kwargs):
        if 'access_file_path' in kwargs:
            kwargs['access_file_path'] = normalize_path(kwargs['access_file_path'])
        super().__init__(*args, **kwargs)
    
    def to_dict(self):
        return {
            'var_name': self.var_name,
            'func_name': self.func_name,
            'access_type': self.access_type,
            'access_file_path': self.access_file_path,
            'access_line_number': self.access_line_number
        }


class CallRelation(db.Model):
    __tablename__ = 'CallRelations'
    
    # 复合主键（保持不变）
    caller_name = db.Column(db.String, primary_key=True)
    callee_name = db.Column(db.String, primary_key=True)
    call_site_file_path = db.Column(db.String, primary_key=True)
    call_site_line_number = db.Column(db.Integer, primary_key=True)
    call_site_column_number = db.Column(db.Integer, primary_key=True)
    
    def __init__(self, *args, **kwargs):
        if 'call_site_file_path' in kwargs:
            kwargs['call_site_file_path'] = normalize_path(kwargs['call_site_file_path'])
        super().__init__(*args, **kwargs)
    
    def to_dict(self):
        return {
            'caller_name': self.caller_name,
            'callee_name': self.callee_name,
            'call_site_file_path': self.call_site_file_path,
            'call_site_line_number': self.call_site_line_number,
            'call_site_column_number': self.call_site_column_number
        }


class DataPointer(db.Model):
    __tablename__ = 'DataPointers'
    
    # 联合主键：pointer_name + file_path
    pointer_name = db.Column(db.String, primary_key=True)
    file_path = db.Column(db.String, primary_key=True)
    points_to_var_name = db.Column(db.String, nullable=False)
    line_number = db.Column(db.Integer, nullable=False)
    
    def __init__(self, *args, **kwargs):
        if 'file_path' in kwargs:
            kwargs['file_path'] = normalize_path(kwargs['file_path'])
        super().__init__(*args, **kwargs)
    
    def to_dict(self):
        return {
            'pointer_name': self.pointer_name,
            'file_path': self.file_path,
            'points_to_var_name': self.points_to_var_name,
            'line_number': self.line_number
        }


class FunctionPointer(db.Model):
    __tablename__ = 'FunctionPointers'
    
    # 联合主键：pointer_name + file_path
    pointer_name = db.Column(db.String, primary_key=True)
    file_path = db.Column(db.String, primary_key=True)
    points_to_func_name = db.Column(db.String, nullable=False)
    line_number = db.Column(db.Integer, nullable=False)
    
    def __init__(self, *args, **kwargs):
        if 'file_path' in kwargs:
            kwargs['file_path'] = normalize_path(kwargs['file_path'])
        super().__init__(*args, **kwargs)
    
    def to_dict(self):
        return {
            'pointer_name': self.pointer_name,
            'file_path': self.file_path,
            'points_to_func_name': self.points_to_func_name,
            'line_number': self.line_number
        }


class Directory(db.Model):
    __tablename__ = 'directories'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('directories.id'), nullable=True)
    
    children = db.relationship('Directory', backref=db.backref('parent', remote_side=[id]))
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'parent_id': self.parent_id,
            'type': 'folder'
        }


class File(db.Model):
    __tablename__ = 'files'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    file_name = db.Column(db.String, nullable=False)
    file_path = db.Column(db.String, nullable=False)
    directory_id = db.Column(db.Integer, db.ForeignKey('directories.id'), nullable=True)
    
    directory = db.relationship('Directory', backref=db.backref('files', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'file_name': self.file_name,
            'file_path': self.file_path,
            'directory_id': self.directory_id,
            'type': 'file'
        }