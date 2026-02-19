from extensions import db
from flask_login import UserMixin
from datetime import datetime

user_roles = db.Table(
    'user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'))
)

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    email = db.Column(db.String(150), unique=True)
    password_hash = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    roles = db.relationship('Role', secondary=user_roles, backref='users')

    def has_role(self, role_name):
        return any(role.name == role_name for role in self.roles)
    
    def has_any_role(self, *roles):
        return any(self.has_role(role) for role in roles)


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)


class Pump(db.Model):
    __tablename__ = 'pumps'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    pump_type = db.Column(db.String(20))  # VERSIL or OTHER
    drawing_path = db.Column(db.String(255))
    
    # New fields
    hp = db.Column(db.Numeric(10, 2))  # Horse Power (1.0, 2.0, etc.)
    phase = db.Column(db.String(10))  # 1, 2, or 3
    pipe_size = db.Column(db.String(100))
    stamping = db.Column(db.String(100))
    stamping_grade = db.Column(db.String(100))
    capacitor = db.Column(db.String(100))  # NEW FIELD
    
    # Phase 1/2 fields
    r_gauge = db.Column(db.String(100))
    r_gauge_weight = db.Column(db.Numeric(10, 4))
    s_gauge = db.Column(db.String(100))
    s_gauge_weight = db.Column(db.Numeric(10, 4))
    
    # Phase 3 fields
    gauge = db.Column(db.String(100))
    weight = db.Column(db.Numeric(10, 4))
    
    deadline_date = db.Column(db.String(10))  # DD/MM/YYYY format
    
    status = db.Column(db.String(50), default='PENDING')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    parts = db.relationship(
        'Part',
        backref='pump',
        cascade='all, delete-orphan',
        passive_deletes=True
    )

class Part(db.Model):
    __tablename__ = 'parts'
    id = db.Column(db.Integer, primary_key=True)
    pump_id = db.Column(db.Integer, db.ForeignKey('pumps.id', ondelete='CASCADE'), nullable=False)
    source = db.Column(db.String(20))
    part_name = db.Column(db.String(200))
    weight = db.Column(db.Numeric(10, 4))
    quantity = db.Column(db.Integer)
    brand = db.Column(db.String(100))
    material = db.Column(db.String(100))

    die_items = db.relationship(
        'DiePatternItem',
        cascade='all, delete-orphan',
        passive_deletes=True
    )

    other_items = db.relationship(
        'OtherItem',
        cascade='all, delete-orphan',
        passive_deletes=True
    )




class DiePatternItem(db.Model):
    __tablename__ = 'die_pattern_items'

    id = db.Column(db.Integer, primary_key=True)

    pump_id = db.Column(db.Integer, db.ForeignKey('pumps.id', ondelete='CASCADE'), nullable=False)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'), nullable=False)

    pattern_cavity = db.Column(db.String(100))
    item_weight = db.Column(db.Numeric(10, 4))

    making_pattern_date = db.Column(db.String(10))
    complete_pattern_date = db.Column(db.String(10))
    send_foundry_pattern_date = db.Column(db.String(10))
    casting_date = db.Column(db.String(10))
    drawing_date = db.Column(db.String(10))
    casting_mc_date = db.Column(db.String(10))
    mc_received_date = db.Column(db.String(10))

    mc_sample_rate = db.Column(db.Numeric(10, 4))
    mc_qty_rate = db.Column(db.Numeric(10, 4))

    status = db.Column(db.Enum('PENDING', 'COMPLETED'), default='PENDING')
    status_override = db.Column(db.Boolean, default=False)

    remark = db.Column(db.Text)

    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())


class OtherItem(db.Model):
    __tablename__ = 'other_items'

    id = db.Column(db.Integer, primary_key=True)

    pump_id = db.Column(db.Integer, db.ForeignKey('pumps.id', ondelete='CASCADE') ,nullable=False)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id', ondelete='CASCADE') ,nullable=False)

    material_specification = db.Column(db.String(255))
    item_weight = db.Column(db.Numeric(10, 4))

    drawing_date = db.Column(db.String(10))
    send_party_drawing_date = db.Column(db.String(10))
    party_name = db.Column(db.String(255))
    party_received_date = db.Column(db.String(10))
    inward_date = db.Column(db.String(10))

    sample_price = db.Column(db.Numeric(10, 4))
    qty_price = db.Column(db.Numeric(10, 4))

    qc_date = db.Column(db.String(10))
    qc_status = db.Column(db.Enum('OK', 'REJECTED'))

    status = db.Column(db.Enum('PENDING', 'COMPLETED'), default='PENDING')
    status_override = db.Column(db.Boolean, default=False)

    remark = db.Column(db.Text)

    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())


class TestingWorkflow(db.Model):
    __tablename__ = 'testing_workflow'

    id = db.Column(db.Integer, primary_key=True)
    pump_id = db.Column(db.Integer, db.ForeignKey('pumps.id', ondelete='CASCADE'), nullable=False)
    date = db.Column(db.String(10), nullable=False)  # DD/MM/YYYY
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.Enum('Assembly', 'Testing', 'Testing Report Date', 'Final Approved', 'Rejected by Boss'), nullable=False)
    remark = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship('User')
    pump = db.relationship('Pump')