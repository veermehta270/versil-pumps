import os
from werkzeug.utils import secure_filename
from flask import Flask, abort, jsonify, render_template, redirect, send_from_directory, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from config import Config
from extensions import db, login_manager, bcrypt
from models import User, Pump, Part, DiePatternItem, OtherItem, TestingWorkflow, Role
from utils.validators import is_valid_ddmmyyyy
from datetime import datetime
from decimal import Decimal, InvalidOperation




app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager.init_app(app)
bcrypt.init_app(app)

def to_decimal(value):
    if value in (None, "", " ","None","null"):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def can_edit_form(form_name):
    """
    form_name: 'die', 'other', 'parts', 'workflow'
    Returns True if user can edit the specified form
    """
    if current_user.has_any_role('BOSS', 'ADMIN'):
        return True

    if form_name == 'die':
        return current_user.has_role('DIE_INCHARGE')

    if form_name == 'other':
        return current_user.has_role('OTHER_INCHARGE')

    return False


def can_view_form(form_name):
    """
    Returns True if user can view the specified form
    DIE_INCHARGE can only view die form
    OTHER_INCHARGE can only view other form
    BOSS/ADMIN can view everything
    """
    if current_user.has_any_role('BOSS', 'ADMIN'):
        return True

    if form_name == 'die':
        return current_user.has_role('DIE_INCHARGE')

    if form_name == 'other':
        return current_user.has_role('OTHER_INCHARGE')

    return False


def parse_deadline_date(date_str):
    """Parse DD/MM/YYYY date string to datetime object"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%d/%m/%Y')
    except:
        return None


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/dashboard')
@login_required
def dashboard():
    # Get all pumps
    pumps = Pump.query.all()
    
    # Separate by status
    pending_pumps = []
    completed_pumps = []
    
    for pump in pumps:
        deadline_date = parse_deadline_date(pump.deadline_date)
        pump_data = {
            'id': pump.id,
            'name': pump.name,
            'pump_type': pump.pump_type,
            'status': pump.status,
            'deadline_date': pump.deadline_date,
            'deadline_obj': deadline_date,
            'has_deadline': deadline_date is not None
        }
        
        if pump.status == 'PENDING':
            pending_pumps.append(pump_data)
        else:
            completed_pumps.append(pump_data)
    
    # Sort: pumps with deadline first (by date), then pumps without deadline
    def sort_by_deadline(pumps_list):
        with_deadline = [p for p in pumps_list if p['has_deadline']]
        without_deadline = [p for p in pumps_list if not p['has_deadline']]
        
        with_deadline.sort(key=lambda x: x['deadline_obj'])
        
        return with_deadline + without_deadline
    
    pending_pumps = sort_by_deadline(pending_pumps)
    completed_pumps = sort_by_deadline(completed_pumps)
    
    return render_template('dashboard/index.html', 
                          pending_pumps=pending_pumps,
                          completed_pumps=completed_pumps)



@app.route('/')
def index():
    """Root route - redirect to login if not authenticated, otherwise dashboard"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and bcrypt.check_password_hash(user.password_hash, request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash("Invalid username or password", "danger")

    return render_template('auth/login.html')


@app.route('/pumps')
@login_required
def pump_list():
    # Filter pumps based on user role
    if current_user.has_any_role('BOSS', 'ADMIN'):
        all_pumps = Pump.query.all()
    elif current_user.has_role('DIE_INCHARGE'):
        all_pumps = Pump.query.all()
    elif current_user.has_role('OTHER_INCHARGE'):
        all_pumps = Pump.query.all()
    else:
        all_pumps = []
    
    # Separate by status
    pending_pumps = [p for p in all_pumps if p.status == 'PENDING']
    completed_pumps = [p for p in all_pumps if p.status == 'COMPLETED']
    
    # Sort function: pumps with deadline first (by date), then without deadline
    def sort_by_deadline(pump_list):
        with_deadline = [p for p in pump_list if p.deadline_date]
        without_deadline = [p for p in pump_list if not p.deadline_date]
        
        # Sort by deadline date (parse DD/MM/YYYY)
        with_deadline.sort(key=lambda p: parse_deadline_date(p.deadline_date))
        
        return with_deadline + without_deadline
    
    # Sort both groups
    pending_pumps = sort_by_deadline(pending_pumps)
    completed_pumps = sort_by_deadline(completed_pumps)
    
    # Combine: pending first, then completed
    pumps = pending_pumps + completed_pumps
    
    return render_template('pumps/list.html', pumps=pumps)

@app.route('/pumps/add', methods=['GET','POST'])
@login_required
def add_pump():
    # Only BOSS/ADMIN can add pumps
    if not current_user.has_any_role('BOSS', 'ADMIN'):
        flash('Access denied', 'danger')
        return redirect(url_for('pump_list'))
    
    
    if request.method == 'POST':
        name = request.form['name']
        pump_type = request.form['pump_type']
        hp = request.form.get('hp')
        phase = request.form.get('phase')
        pipe_size = request.form.get('pipe_size')
        stamping = request.form.get('stamping')
        stamping_grade = request.form.get('stamping_grade')
        capacitor = request.form.get('capacitor')  # NEW FIELD
        deadline_date = request.form.get('deadline_date', '').strip()
        
        # Validate deadline date if provided
        if deadline_date and not is_valid_ddmmyyyy(deadline_date):
            flash('Invalid deadline date format. Use DD/MM/YYYY', 'danger')
            return redirect(url_for('add_pump'))
        
        # Handle file upload
        file = request.files.get('drawing')
        filename = None
        if file and file.filename:
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)

        pump = Pump(
            name=name,
            pump_type=pump_type,
            hp=hp,
            phase=phase,
            pipe_size=pipe_size,
            stamping=stamping,
            stamping_grade=stamping_grade,
            capacitor=capacitor,  # NEW FIELD
            deadline_date=deadline_date if deadline_date else None,
            drawing_path=filename,
            status='PENDING',
            created_by=current_user.id
        )
        
        # Phase-specific fields - FIX: Don't use to_decimal() on gauge string fields
        if phase in ['1', '2']:
            pump.r_gauge = request.form.get('r_gauge') or None  # FIXED: Direct string assignment
            pump.r_gauge_weight = to_decimal(request.form.get('r_gauge_weight'))
            pump.s_gauge = request.form.get('s_gauge') or None  # FIXED: Direct string assignment
            pump.s_gauge_weight = to_decimal(request.form.get('s_gauge_weight'))

        elif phase == '3':
            pump.gauge = request.form.get('gauge') or None  # FIXED: Direct string assignment
            pump.weight = to_decimal(request.form.get('weight'))

        db.session.add(pump)
        db.session.commit()

        flash('Pump created successfully', 'success')
        return redirect(url_for('pump_list'))
    
    return render_template('pumps/add.html', pump=None)




@app.route('/pumps/<int:pump_id>/info', methods=['GET', 'POST'])
@login_required
def pump_info(pump_id):
    # Only BOSS/ADMIN can view/edit pump info
    if not current_user.has_any_role('BOSS', 'ADMIN'):
        flash('Access denied', 'danger')
        return redirect(url_for('pump_list'))
    
    pump = Pump.query.get_or_404(pump_id)
    
    if request.method == 'POST':
        # CRITICAL: Check if pump is COMPLETED before processing ANY edits
        if pump.status != 'PENDING':
            flash('This pump is COMPLETED and cannot be edited.', 'danger')
            return redirect(url_for('pump_info', pump_id=pump_id))

        phase = request.form.get('phase')
        pump.name = request.form['name']
        pump.hp = request.form.get('hp')
        pump.phase = phase
        pump.pipe_size = request.form.get('pipe_size')
        pump.stamping = request.form.get('stamping')
        pump.stamping_grade = request.form.get('stamping_grade')
        pump.capacitor = request.form.get('capacitor')
        deadline_date = request.form.get('deadline_date', '').strip()
        
        if deadline_date and not is_valid_ddmmyyyy(deadline_date):
            flash('Invalid deadline date format. Use DD/MM/YYYY', 'danger')
            return redirect(url_for('pump_info', pump_id=pump_id))
        
        pump.deadline_date = deadline_date if deadline_date else None
        
        # === GAUGE FIELDS: Update only relevant ones ===
        if phase in ['1', '2']:
            pump.r_gauge = request.form.get('r_gauge') or None
            pump.r_gauge_weight = to_decimal(request.form.get('r_gauge_weight'))
            pump.s_gauge = request.form.get('s_gauge') or None
            pump.s_gauge_weight = to_decimal(request.form.get('s_gauge_weight'))
            
            # Clear 3-phase fields when in 1/2 phase
            pump.gauge = None
            pump.weight = None

        elif phase == '3':
            pump.gauge = request.form.get('gauge') or None
            pump.weight = to_decimal(request.form.get('weight'))
            
            # Clear 1/2-phase fields when in 3 phase
            pump.r_gauge = None
            pump.r_gauge_weight = None
            pump.s_gauge = None
            pump.s_gauge_weight = None

        # === FILE UPLOAD ===
        file = request.files.get('drawing')
        if file and file.filename:
            if pump.drawing_path:
                old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], pump.drawing_path)
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)
            
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            pump.drawing_path = filename
        
        db.session.commit()
        flash('Pump info updated successfully', 'success')
        return redirect(url_for('pump_info', pump_id=pump_id))

    # GET request - show the form
    read_only = (pump.status != 'PENDING')
    return render_template('pumps/add.html', pump=pump, read_only=read_only)



# ==================== PARTS ROUTES ====================

@app.route('/pumps/<int:pump_id>/parts', methods=['GET'])
@login_required
def add_parts(pump_id):
    # Only BOSS/ADMIN can view/edit parts
    if not current_user.has_any_role('BOSS', 'ADMIN'):
        flash('Access denied', 'danger')
        return redirect(url_for('pump_list'))
    
    pump = Pump.query.get_or_404(pump_id)
    read_only = pump.status != 'PENDING'
    
    return render_template('pumps/add_parts.html', pump=pump, read_only=read_only)


@app.route('/api/pumps/<int:pump_id>/parts', methods=['GET'])
@login_required
def get_parts(pump_id):
    parts = Part.query.filter_by(pump_id=pump_id).all()
    parts_data = []
    for part in parts:
        parts_data.append({
            'id': part.id,
            'source': part.source,
            'part_name': part.part_name,
            'weight': float(part.weight) if part.weight else 0,
            'quantity': part.quantity,
            'brand': part.brand,
            'material': part.material
        })
    return jsonify({'parts': parts_data})


@app.route('/api/pumps/<int:pump_id>/parts/save', methods=['POST'])
@login_required
def save_part(pump_id):
    try:
        pump = Pump.query.get_or_404(pump_id)

        if pump.status != 'PENDING':
            return jsonify({'success': False, 'error': 'Cannot edit parts in current pump status'}), 403

        if not current_user.has_any_role('BOSS', 'ADMIN'):
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        data = request.json
        part_id = data.get('id')
        
        if part_id:
            # Update existing part
            part = Part.query.get(part_id)
            if part and part.pump_id == pump_id:
                part.part_name = data.get('part_name', '')
                part.weight = to_decimal(data.get('weight'))
                part.quantity = int(data.get('quantity')) if data.get('quantity') not in ("", None) else None
                part.brand = data.get('brand', '')
                part.material = data.get('material', '')
                part.source = data.get('source', 'OTHER')
            else:
                return jsonify({'success': False, 'error': 'Part not found'}), 404
        else:
            # Create new part
            part = Part(
                pump_id=pump_id,
                source=data.get('source', 'OTHER'),
                part_name=data.get('part_name', ''),
                weight=to_decimal(data.get('weight', 0)),
                quantity=int(data.get('quantity')) if data.get('quantity') not in ("", None) else None,
                brand=data.get('brand', ''),
                material=data.get('material', '')
            )
            db.session.add(part)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'id': part.id,
            'message': 'Part saved successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/pumps/<int:pump_id>/parts/<int:part_id>', methods=['DELETE'])
@login_required
def delete_part(pump_id, part_id):
    try:
        pump = Pump.query.get_or_404(pump_id)
        
        if pump.status != 'PENDING':
            return jsonify({'success': False, 'error': 'Cannot delete parts in current pump status'}), 403
        
        if not current_user.has_any_role('BOSS', 'ADMIN'):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        part = Part.query.get(part_id)
        if part and part.pump_id == pump_id:
            db.session.delete(part)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Part deleted'})
        return jsonify({'success': False, 'error': 'Part not found'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== DIE & PATTERN ROUTES ====================

@app.route('/pumps/<int:pump_id>/die-pattern', methods=['GET'])
@login_required
def die_pattern_form(pump_id):
    if not can_view_form('die'):
        flash('Access denied', 'danger')
        return redirect(url_for('pump_list'))
    
    pump = Pump.query.get_or_404(pump_id)

    versil_parts = Part.query.filter_by(
        pump_id=pump.id,
        source='VERSIL'
    ).all()

    items = DiePatternItem.query.filter_by(
        pump_id=pump.id
    ).all()

    can_edit = (
        pump.status == 'PENDING'
        and can_edit_form('die')
    )

    return render_template(
        'die_pattern/form.html',
        pump=pump,
        versil_parts=versil_parts,
        items=items,
        read_only=not can_edit
    )


@app.route('/pumps/<int:pump_id>/die-pattern', methods=['POST'])
@login_required
def save_die_pattern(pump_id):
    pump = Pump.query.get_or_404(pump_id)

    if not can_edit_form('die'):
        return jsonify({'success': False, 'message': 'Access denied'}), 403

    if pump.status != 'PENDING':
        return jsonify({'success': False, 'message': 'Cannot edit pump in current status'}), 403

    rows = request.json.get('rows', [])

    # Validate dates FIRST
    DATE_FIELDS = [
        'making_pattern_date',
        'complete_pattern_date',
        'send_foundry_pattern_date',
        'casting_date',
        'drawing_date',
        'casting_mc_date',
        'mc_received_date'
    ]

    for row in rows:
        for field in DATE_FIELDS:
            value = row.get(field)
            if value and not is_valid_ddmmyyyy(value):
                return jsonify({
                    'success': False,
                    'message': f'Invalid date format for {field}. Use DD/MM/YYYY'
                }), 400

    # Get existing items for this pump
    existing_items = DiePatternItem.query.filter_by(pump_id=pump.id).all()
    processed_ids = []

    for row in rows:
        part_id = row.get('part_id')
        if not part_id:
            continue

        item = DiePatternItem.query.filter_by(
            pump_id=pump.id,
            part_id=part_id
        ).first()

        if not item:
            item = DiePatternItem(
                pump_id=pump.id,
                part_id=part_id
            )

        # Field mapping
        item.pattern_cavity = row.get('pattern_cavity') or None
        item.item_weight = to_decimal(row.get('item_weight'))
        item.making_pattern_date = row.get('making_pattern_date') or None
        item.complete_pattern_date = row.get('complete_pattern_date') or None
        item.send_foundry_pattern_date = row.get('send_foundry_pattern_date') or None
        item.casting_date = row.get('casting_date') or None
        item.drawing_date = row.get('drawing_date') or None
        item.casting_mc_date = row.get('casting_mc_date') or None
        item.mc_received_date = row.get('mc_received_date') or None
        item.mc_sample_rate = to_decimal(row.get('mc_sample_rate'))
        item.mc_qty_rate = to_decimal(row.get('mc_qty_rate'))
        item.remark = row.get('remark') or None
        item.status = row.get('status') or 'PENDING'

        db.session.add(item)
        if item.id:
            processed_ids.append(item.id)

    # Delete items that were removed from the form
    for existing_item in existing_items:
        if existing_item.id not in processed_ids:
            db.session.delete(existing_item)

    db.session.commit()

    return jsonify({'success': True, 'message': 'Die & Pattern saved successfully'})


# ==================== OTHER ITEMS ROUTES ====================

@app.route('/pumps/<int:pump_id>/other-items', methods=['GET'])
@login_required
def other_items_form(pump_id):
    if not can_view_form('other'):
        flash('Access denied', 'danger')
        return redirect(url_for('pump_list'))
    
    pump = Pump.query.get_or_404(pump_id)

    versil_parts = Part.query.filter_by(
        pump_id=pump.id,
        source='VERSIL'
    ).all()

    items = OtherItem.query.filter_by(
        pump_id=pump.id
    ).all()

    can_edit = (
        pump.status == 'PENDING'
        and can_edit_form('other')
    )

    return render_template(
        'other_items/form.html',
        pump=pump,
        versil_parts=versil_parts,
        items=items,
        read_only=not can_edit
    )


@app.route('/pumps/<int:pump_id>/other-items', methods=['POST'])
@login_required
def save_other_items(pump_id):
    pump = Pump.query.get_or_404(pump_id)

    if pump.status != 'PENDING':
        return jsonify({'success': False, 'message': 'Cannot edit pump in current status'}), 403

    if not can_edit_form('other'):
        return jsonify({'success': False, 'message': 'Access denied'}), 403

    rows = request.json.get('rows', [])

    # Validate dates FIRST
    DATE_FIELDS = [
        'drawing_date',
        'send_party_drawing_date',
        'party_received_date',
        'inward_date',
        'qc_date',
    ]

    for row in rows:
        for field in DATE_FIELDS:
            value = row.get(field)
            if value and not is_valid_ddmmyyyy(value):
                return jsonify({
                    'success': False,
                    'message': f'Invalid date format for {field}. Use DD/MM/YYYY'
                }), 400

    # Get existing items for this pump
    existing_items = OtherItem.query.filter_by(pump_id=pump.id).all()
    processed_ids = []

    for row in rows:
        part_id = row.get('part_id')
        if not part_id:
            continue

        item = OtherItem.query.filter_by(
            pump_id=pump.id,
            part_id=part_id
        ).first()

        if not item:
            item = OtherItem(
                pump_id=pump.id,
                part_id=part_id
            )

        # Field mapping
        item.material_specification = row.get('material_specification') or None
        item.item_weight = to_decimal(row.get('item_weight'))
        item.drawing_date = row.get('drawing_date') or None
        item.send_party_drawing_date = row.get('send_party_drawing_date') or None
        item.party_name = row.get('party_name') or None
        item.party_received_date = row.get('party_received_date') or None
        item.inward_date = row.get('inward_date') or None
        item.sample_price = to_decimal(row.get('sample_price'))
        item.qty_price = to_decimal(row.get('qty_price'))
        item.qc_date = row.get('qc_date') or None
        item.qc_status = row.get('qc_status') or None
        item.remark = row.get('remark') or None
        item.status = row.get('status') or 'PENDING'

        db.session.add(item)
        if item.id:
            processed_ids.append(item.id)

    # Delete items that were removed from the form
    for existing_item in existing_items:
        if existing_item.id not in processed_ids:
            db.session.delete(existing_item)

    db.session.commit()

    return jsonify({'success': True, 'message': 'Other items saved successfully'})


# ==================== WORKFLOW ROUTES ====================

@app.route('/pumps/<int:pump_id>/workflow', methods=['GET'])
@login_required
def workflow_form(pump_id):

    
    if not current_user.has_any_role('BOSS','ADMIN'):
        flash('Access denied', 'danger')
        return redirect(url_for('pump_list'))


    pump = Pump.query.get_or_404(pump_id)
    
    activities = TestingWorkflow.query.filter_by(
        pump_id=pump.id
    ).order_by(TestingWorkflow.created_at.asc()).all()
    
    # Get today's date in DD/MM/YYYY format
    today = datetime.now()
    today_date = today.strftime('%d/%m/%Y')

    # Only editable when status is PENDING and user is BOSS/ADMIN
    can_edit = current_user.has_any_role('BOSS', 'ADMIN') and pump.status == 'PENDING'
    
    # Check if user is boss
    is_boss = current_user.has_role('BOSS')
    
    return render_template(
        'workflow/form.html',
        pump=pump,
        activities=activities,
        today_date=today_date,
        read_only=not can_edit,
        is_boss=is_boss
    )


@app.route('/pumps/<int:pump_id>/workflow', methods=['POST'])
@login_required
def save_workflow(pump_id):
    pump = Pump.query.get_or_404(pump_id)
    
    if pump.status != 'PENDING':
        return jsonify({'success': False, 'message': 'Invalid pump status'}), 403
    
    if not current_user.has_any_role('BOSS', 'ADMIN'):
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    data = request.json
    rows = data.get('rows', [])
    
    # Validate dates
    for row in rows:
        date_str = row.get('date')
        if date_str and not is_valid_ddmmyyyy(date_str):
            return jsonify({
                'success': False,
                'message': f'Invalid date format: {date_str}. Use DD/MM/YYYY'
            }), 400
    
    # Get existing activities count
    existing_count = TestingWorkflow.query.filter_by(pump_id=pump.id).count()
    
    # Validate action sequence
    for idx, row in enumerate(rows):
        action = row.get('action')
        position = existing_count + idx
        
        if position == 0 and action != 'Assembly':
            return jsonify({
                'success': False,
                'message': 'First action must be Assembly'
            }), 400
        
        if position == 1 and action != 'Testing':
            return jsonify({
                'success': False,
                'message': 'Second action must be Testing'
            }), 400
    
    # Save new activities
    for row in rows:
        activity = TestingWorkflow(
            pump_id=pump.id,
            date=row.get('date'),
            user_id=current_user.id,
            action=row.get('action'),
            remark=row.get('remark')
        )
        db.session.add(activity)
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Workflow saved successfully'})

@app.route('/pumps/<int:pump_id>/workflow/final-approve', methods=['POST'])
@login_required
def final_approve_workflow(pump_id):
    try:
        if not current_user.has_role('BOSS'):
            return jsonify({
                'success': False,
                'message': 'You are not authorized to approve.'
            }), 403

        pump = Pump.query.get_or_404(pump_id)

        if pump.status != 'PENDING':
            return jsonify({
                'success': False,
                'message': 'Pump is not in pending state.'
            }), 400

        data = request.get_json(silent=True) or {}
        comment = data.get('comment', '').strip()

        if not comment:
            return jsonify({
                'success': False,
                'message': 'Approval comment is required.'
            }), 400

        pump.status = 'COMPLETED'

        approval_entry = TestingWorkflow(
            pump_id=pump.id,
            date=datetime.now().strftime('%d/%m/%Y'),
            user_id=current_user.id,
            action='Final Approved',
            remark=comment
        )

        db.session.add(approval_entry)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Pump approved successfully.'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/pumps/<int:pump_id>/workflow/reject', methods=['POST'])
@login_required
def reject_workflow(pump_id):
    try:
        if not current_user.has_role('BOSS'):
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        pump = Pump.query.get_or_404(pump_id)
        
        if pump.status != 'COMPLETED':
            return jsonify({'success': False, 'message': 'Can only reject approved pumps'}), 400
        
        data = request.get_json(silent=True) or {}
        comment = data.get('comment', '').strip()
        
        if not comment:
            return jsonify({'success': False, 'message': 'Comment is required'}), 400
        
        pump.status = 'PENDING'
        
        today = datetime.now()
        rejection_entry = TestingWorkflow(
            pump_id=pump.id,
            date=today.strftime('%d/%m/%Y'),
            user_id=current_user.id,
            action='Rejected by Boss',
            remark=comment
        )
        db.session.add(rejection_entry)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Pump rejected and sent back for revision'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

# ==================== OTHER ROUTES ====================

@app.route('/pumps/<int:pump_id>/delete', methods=['POST'])
@login_required
def delete_pump(pump_id):

    if not current_user.has_any_role('BOSS', 'ADMIN'):
        flash('You do not have permission to delete pumps.', 'danger')
        return redirect(url_for('pump_list'))

    try:
        pump = Pump.query.get_or_404(pump_id)
        db.session.delete(pump)  # CASCADE handles children
        db.session.commit()

        flash(f'Pump "{pump.name}" deleted successfully.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting pump: {str(e)}', 'danger')

    return redirect(url_for('pump_list'))


@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/pumps/<int:pump_id>/manage')
@login_required
def pump_management(pump_id):
    pump = Pump.query.get_or_404(pump_id)
    return render_template('pumps/management.html', pump=pump)




@app.route('/admin/users/add', methods=['GET', 'POST'])
@login_required
def add_user():
    if not current_user.has_any_role('ADMIN', 'BOSS'):
        abort(403)

    roles = Role.query.order_by(Role.name).all()

    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        role_id = request.form['role_id']

        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('add_user'))

        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

        user = User(
            username=username,
            password_hash=password_hash
        )

        role = Role.query.get(role_id)
        user.roles.append(role)

        db.session.add(user)
        db.session.commit()

        flash('User created successfully', 'success')
        return redirect(url_for('dashboard'))

    return render_template('admin/add_user.html', roles=roles)



@app.route('/admin/users', methods=['GET'])
@login_required
def manage_users():
    if not current_user.has_any_role('ADMIN', 'BOSS'):
        abort(403)
    
    users = User.query.order_by(User.username).all()
    return render_template('admin/manage_users.html', users=users)


@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.has_any_role('ADMIN', 'BOSS'):
        abort(403)
    
    user = User.query.get_or_404(user_id)
    
    # Prevent deletion of the last admin/boss
    if user.has_any_role('ADMIN', 'BOSS'):
        admin_boss_count = User.query.join(User.roles).filter(
            Role.name.in_(['ADMIN', 'BOSS'])
        ).distinct().count()
        
        if admin_boss_count <= 1:
            flash('Cannot delete the last admin/boss user in the system', 'danger')
            return redirect(url_for('manage_users'))
    
    username = user.username
    
    # Check if user is deleting themselves
    is_self_delete = (user.id == current_user.id)
    
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User "{username}" deleted successfully', 'success')
    
    # If admin deleted themselves, redirect to logout
    if is_self_delete:
        return redirect(url_for('logout'))
    
    return redirect(url_for('manage_users'))




# REPLACE THE LAST SECTION OF app.py (at the very bottom)
# FROM:
# if __name__ == '__main__':
#     app.run(host="0.0.0.0", debug=True, port=5000)

# TO:
if __name__ == '__main__':
    # This section is no longer needed since we're using run.py
    # But keep it for backward compatibility
    from config import Config
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )