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


class EditTransactionForm(FlaskForm):
    type = StringField('Type', render_kw={'readonly': True})
    asset_name = StringField('Asset Name', render_kw={'readonly': True})
    person_name = StringField('Person', render_kw={'readonly': True})
    start_time = DateField('Start Time', render_kw={'readonly': True})
    # end_time = DateField('End Time', validators=[DataRequired()])
    end_time = DateField('End Time', format='%Y-%m-%d', validators=[DataRequired()])
    status = SelectField('Status', choices=[('In Use', 'In Use'), ('In Store', 'In Store')],
                         validators=[DataRequired()])
    submit = SubmitField('Update')

class UploadReportForm(FlaskForm):
    wo = StringField('WorkOrder', render_kw={'readonly': True})
    pn = StringField('ProductionNumber', render_kw={'readonly': True})
    csn = StringField('Chassis S/N', render_kw={'readonly': True})
    msn = StringField('Motherboard S/N', validators=[DataRequired()])
    cpu = StringField('CPU', validators=[DataRequired()],render_kw={'style': 'width: 200px'})
    mem1 = StringField('Memory Slot1',render_kw={'style': 'width: 200px'})
    mem2 = StringField('Memory Slot2',render_kw={'style': 'width: 200px'})
    mem3 = StringField('Memory Slot3',render_kw={'style': 'width: 200px'})
    mem4 = StringField('Memory Slot4',render_kw={'style': 'width: 200px'})
    gpu1 = StringField('External GPU1')
    gpu2 = StringField('External GPU2')
    sata1 = StringField('SATA1')
    sata2 = StringField('SATA2')
    sata3 = StringField('SATA3')
    sata4 = StringField('SATA4')
    m21 = StringField('M.2 Slot1')
    m22 = StringField('M.2 Slot2')
    wifi = StringField('Wifi Module')
    fg5g = StringField('4G/5G Module')
    can = StringField('CAN Module')
    other = StringField('Other Module')
    note  = StringField('Notes',widget=TextArea())
    report = HiddenField('Report File')
    submit = SubmitField('Update')

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

class AddTransactionForm(FlaskForm):
    type = SelectField('Type', validators=[DataRequired()],
                       choices=[('harddisk', 'Hard Disk'), ('testingcard', 'Card')])
    asset_name = QuerySelectField(label='Asset Name', validators=[DataRequired()], query_factory=get_assets,
                                  allow_blank=True)
    #person_name = StringField('Person', validators=[DataRequired()])
    person_name = StringField('Person', validators=[DataRequired()], widget=TextArea())
    start_time = DateField('Start Time', format='%Y-%m-%d', validators=[DataRequired()])
    #start_time = DateField('Start Time', format='%m/%d/%y', render_kw={'placeholder': '6/20/15 for June 20, 2015'})
    end_time = HiddenField('End Time')
    status = SelectField('Status', validators=[DataRequired()], choices=[('In Use', 'In Use')])
    submit = SubmitField('Add')


class AddAssetForm(FlaskForm):
    wo = StringField('WorkOrder', validators=[DataRequired()])
    pn = StringField('Production Number', validators=[DataRequired()])
    csn = StringField('Chassis Serial Number', validators=[DataRequired()], widget=TextArea())
    asid= HiddenField('Assembler ID')
    insid= HiddenField('Inspector ID')
    astime=HiddenField('Assembling Time')
    intime=HiddenField('Inspection Time')
    status= HiddenField('Status')
    submit = SubmitField('Create New WorkOrder')
