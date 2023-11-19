from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, HiddenField, SelectField, ValidationError,BooleanField
from wtforms.validators import DataRequired, Length, InputRequired
from wtforms.fields.html5 import DateField
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.widgets import TextArea
from app.asset.models import WorkOrder, Production
from app.auth.forms  import get_userrole,get_usersname

class UploadReportForm(FlaskForm):
    wo = StringField('WorkOrder#', render_kw={'readonly': True,'style': 'width: 200px'})
    pn = StringField('Product Model', render_kw={'readonly': True,'style': 'width: 200px'})
    csn = StringField('Chassis S/N', render_kw={'readonly': True,'style': 'width: 200px'})
    msn = StringField('Motherboard S/N', validators=[DataRequired(),Length(max=100)],render_kw={'style': 'width: 200px'})
    cpu = StringField('CPU', validators=[DataRequired()],render_kw={'style': 'width: 200px'})
    mem1 = StringField('Memory Slot1',validators=[Length(max=256)],render_kw={'style': 'width: 200px'})
    mem2 = StringField('Memory Slot2',validators=[Length(max=256)],render_kw={'style': 'width: 200px'})
    mem3 = StringField('Memory Slot3',validators=[Length(max=256)],render_kw={'style': 'width: 200px'})
    mem4 = StringField('Memory Slot4',validators=[Length(max=256)],render_kw={'style': 'width: 200px'})
    gpu1 = StringField('External GPU1',validators=[Length(max=100)],render_kw={'style': 'width: 200px'})
    gpu2 = StringField('External GPU2',validators=[Length(max=100)],render_kw={'style': 'width: 200px'})
    sata1 = StringField('SATA1',validators=[Length(max=100)],render_kw={'style': 'width: 200px'})
    sata2 = StringField('SATA2',validators=[Length(max=100)],render_kw={'style': 'width: 200px'})
    sata3 = StringField('SATA3',validators=[Length(max=100)],render_kw={'style': 'width: 200px'})
    sata4 = StringField('SATA4',validators=[Length(max=100)],render_kw={'style': 'width: 200px'})
    m21 = StringField('M.2 Slot1',validators=[Length(max=100)],render_kw={'style': 'width: 200px'})
    m22 = StringField('M.2 Slot2',validators=[Length(max=100)],render_kw={'style': 'width: 200px'})
    wifi = StringField('Wifi Module',validators=[Length(max=100)],render_kw={'style': 'width: 200px'})
    fg5g = StringField('4G/5G Module',validators=[Length(max=100)],render_kw={'style': 'width: 200px'})
    can = StringField('CAN Module',validators=[Length(max=100)],render_kw={'style': 'width: 200px'})
    other = StringField('Other Module',validators=[Length(max=100)],render_kw={'style': 'width: 200px'})
    note  = StringField('Notes',validators=[Length(max=256)],widget=TextArea())
    report = StringField('Report File',validators=[Length(max=512000)],widget=TextArea(),render_kw={'style': 'width: 400px','readonly': True})

    submit = SubmitField('Update')

class ReviewReportForm(FlaskForm):
    wo = StringField('WorkOrder#', render_kw={'readonly': True})
    pn = StringField('Product Model', render_kw={'readonly': True})
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
    action = SelectField('Approve or Deny',choices=[('0','Approve'),('1','Deny')])
    submit = SubmitField('Confirm')
  

class ReviewReportFileForm(FlaskForm):
    
    report = StringField('Report File',widget=TextArea(),render_kw={'style': 'width: 400px','readonly': True})

class AddWorkorderForm(FlaskForm):
    wo = StringField('WorkOrder#', validators=[DataRequired(),Length(max=100)])
    customers = StringField('Customer Name', validators=[DataRequired(),Length(max=100)])
    pn = StringField('Product Model', validators=[DataRequired(),Length(max=100)])
    csn = StringField('Chassis Serial Number', validators=[DataRequired(),Length(max=100)], widget=TextArea())
    cpuinstall = BooleanField('CPU Installation')
    memoryinstall = BooleanField('Memory Installation')
    gpuinstall = BooleanField('GPU Installation')
    wifiinstall = BooleanField('Wifi Installation')
    caninstall = BooleanField('CAN Installation')
    mezioinstall = BooleanField('MezIO Installation')
    osinstall = StringField('Installation OS Name', validators=[Length(max=40)])
    operator = QuerySelectField('Operator Name', query_factory=get_usersname,allow_blank=True)
    asid= HiddenField('Assembler ID')
    insid= HiddenField('Inspector ID')
    astime=HiddenField('Assembling Time')
    intime=HiddenField('Inspection Time')
    status= HiddenField('Status')
    submit = SubmitField('Create New WorkOrder')

class EditOneComputerForm(FlaskForm):
    wo = StringField('WorkOrder#', validators=[DataRequired(),Length(max=100)])
    customers = StringField('Customer Name', validators=[DataRequired(),Length(max=100)])
    pn = StringField('Product Model', validators=[DataRequired(),Length(max=100)])
    csn = StringField('Chassis Serial Number', validators=[DataRequired(),Length(max=100)])
    cpuinstall = BooleanField('CPU Installation')
    memoryinstall = BooleanField('Memory Installation')
    gpuinstall = BooleanField('GPU Installation')
    wifiinstall = BooleanField('Wifi Installation')
    caninstall = BooleanField('CAN Installation')
    mezioinstall = BooleanField('MezIO Installation')
    osinstall = StringField('Installation OS Name', validators=[Length(max=40)])
    operator = QuerySelectField('Operator Name', query_factory=get_usersname,allow_blank=True)
    asid= HiddenField('Assembler ID')
    insid= HiddenField('Inspector ID')
    astime=HiddenField('Assembling Time')
    intime=HiddenField('Inspection Time')
    status= HiddenField('Status')
    submit = SubmitField('Update')
