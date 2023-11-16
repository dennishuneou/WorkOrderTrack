from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, HiddenField, SelectField, ValidationError
from wtforms.validators import DataRequired
from wtforms.fields.html5 import DateField
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.widgets import TextArea

from app.asset.models import WorkOrder, Production


def check_if_asset_exist(form, field):
    asset = Asset.query.filter_by(asset_name=field.data).first()
    if asset:
        raise ValidationError('Asset Already Exists')


def get_assets():
    return Asset.query.all()

class UploadReportForm(FlaskForm):
    wo = StringField('WorkOrder', render_kw={'readonly': True,'style': 'width: 200px'})
    pn = StringField('ProductionNumber', render_kw={'readonly': True,'style': 'width: 200px'})
    csn = StringField('Chassis S/N', render_kw={'readonly': True,'style': 'width: 200px'})
    msn = StringField('Motherboard S/N', validators=[DataRequired()],render_kw={'style': 'width: 200px'})
    cpu = StringField('CPU', validators=[DataRequired()],render_kw={'style': 'width: 200px'})
    mem1 = StringField('Memory Slot1',render_kw={'style': 'width: 200px'})
    mem2 = StringField('Memory Slot2',render_kw={'style': 'width: 200px'})
    mem3 = StringField('Memory Slot3',render_kw={'style': 'width: 200px'})
    mem4 = StringField('Memory Slot4',render_kw={'style': 'width: 200px'})
    gpu1 = StringField('External GPU1',render_kw={'style': 'width: 200px'})
    gpu2 = StringField('External GPU2',render_kw={'style': 'width: 200px'})
    sata1 = StringField('SATA1',render_kw={'style': 'width: 200px'})
    sata2 = StringField('SATA2',render_kw={'style': 'width: 200px'})
    sata3 = StringField('SATA3',render_kw={'style': 'width: 200px'})
    sata4 = StringField('SATA4',render_kw={'style': 'width: 200px'})
    m21 = StringField('M.2 Slot1',render_kw={'style': 'width: 200px'})
    m22 = StringField('M.2 Slot2',render_kw={'style': 'width: 200px'})
    wifi = StringField('Wifi Module',render_kw={'style': 'width: 200px'})
    fg5g = StringField('4G/5G Module',render_kw={'style': 'width: 200px'})
    can = StringField('CAN Module',render_kw={'style': 'width: 200px'})
    other = StringField('Other Module',render_kw={'style': 'width: 200px'})
    note  = StringField('Notes',widget=TextArea())
    report = StringField('Report File',widget=TextArea(),render_kw={'style': 'width: 400px','readonly': True})

    submit = SubmitField('Update')

class ReviewReportForm(FlaskForm):
    wo = StringField('WorkOrder', render_kw={'readonly': True})
    pn = StringField('ProductionNumber', render_kw={'readonly': True})
    csn = StringField('Chassis S/N', render_kw={'readonly': True})
    msn = StringField('Motherboard S/N', validators=[DataRequired()],render_kw={'readonly': True})
    cpu = StringField('CPU', validators=[DataRequired()],render_kw={'style': 'width: 200px','readonly': True})
    mem1 = StringField('Memory Slot1',render_kw={'style': 'width: 200px', 'readonly': True})
    mem2 = StringField('Memory Slot2',render_kw={'style': 'width: 200px', 'readonly': True})
    mem3 = StringField('Memory Slot3',render_kw={'style': 'width: 200px', 'readonly': True})
    mem4 = StringField('Memory Slot4',render_kw={'style': 'width: 200px',  'readonly': True})
    gpu1 = StringField('External GPU1',render_kw={'readonly': True})
    gpu2 = StringField('External GPU2',render_kw={'readonly': True})
    sata1 = StringField('SATA1',render_kw={'readonly': True})
    sata2 = StringField('SATA2',render_kw={'readonly': True})
    sata3 = StringField('SATA3',render_kw={'readonly': True})
    sata4 = StringField('SATA4',render_kw={'readonly': True})
    m21 = StringField('M.2 Slot1',render_kw={'readonly': True})
    m22 = StringField('M.2 Slot2',render_kw={'readonly': True})
    wifi = StringField('Wifi Module',render_kw={'readonly': True})
    fg5g = StringField('4G/5G Module',render_kw={'readonly': True})
    can = StringField('CAN Module',render_kw={'readonly': True})
    other = StringField('Other Module',render_kw={'readonly': True})
    note  = StringField('Notes',widget=TextArea(),render_kw={'readonly': True})
    report = StringField('Report File',widget=TextArea(),render_kw={'style': 'width: 400px','readonly': True})
    submit = SubmitField('Confirm')

class ReviewReportFileForm(FlaskForm):
    
    report = StringField('Report File',widget=TextArea(),render_kw={'style': 'width: 400px','readonly': True})

class EditWorkOrderForm(FlaskForm):
    wo = StringField('Type', render_kw={'readonly': True})
    asset_name = StringField('Asset Name', render_kw={'readonly': True})
    person_name = StringField('Person', render_kw={'readonly': True})
    start_time = DateField('Start Time', render_kw={'readonly': True})
    # end_time = DateField('End Time', validators=[DataRequired()])
    end_time = DateField('End Time', format='%Y-%m-%d', validators=[DataRequired()])
    status = SelectField('Status', choices=[('In Use', 'In Use'), ('In Store', 'In Store')],
                         validators=[DataRequired()])
    submit = SubmitField('Update')

class AddWorkorderForm(FlaskForm):
    wo = StringField('WorkOrder', validators=[DataRequired()])
    customers = StringField('Customer', validators=[DataRequired()])
    pn = StringField('Production Number', validators=[DataRequired()])
    csn = StringField('Chassis Serial Number', validators=[DataRequired()], widget=TextArea())
    asid= HiddenField('Assembler ID')
    insid= HiddenField('Inspector ID')
    astime=HiddenField('Assembling Time')
    intime=HiddenField('Inspection Time')
    status= HiddenField('Status')
    submit = SubmitField('Create New WorkOrder')
