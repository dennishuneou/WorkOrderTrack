from flask_login import login_required
from app.asset.forms import EditWorkOrderForm, AddWorkorderForm, UploadReportForm, ReviewReportForm, ReviewReportFileForm
from app.asset import main
from app.asset.models import Transaction, WorkOrder, Production
from flask import render_template, flash, request, redirect, url_for
from app import db
#Dennis
#workorder status, unassigned -1, processing 0, waiting for inspection 1 finished 2.
from flask_login import current_user
import datetime
from sqlalchemy import func
@main.route('/')
@login_required
def display_workorders():
    #transactions = Transaction.query.all()
    todoworkorder = WorkOrder.query.filter_by(status=-1)
    query1 = WorkOrder.query.filter_by(asid=current_user.id, status=0)
    query2 =  WorkOrder.query.filter_by(asid=current_user.id, status=1)
    processing = query1.union(query2)
    completed = WorkOrder.query.filter(func.DATE(WorkOrder.intime) == func.DATE(datetime.datetime.today()),WorkOrder.asid==current_user.id,WorkOrder.status == 2)
    completed7day = WorkOrder.query.filter((func.DATE(WorkOrder.intime)) >= (func.DATE(datetime.datetime.today())-7),WorkOrder.asid==current_user.id,WorkOrder.status == 2)
    completed28day = WorkOrder.query.filter((func.DATE(WorkOrder.intime)) >= (func.DATE(datetime.datetime.today())-28),WorkOrder.asid==current_user.id,WorkOrder.status == 2)
    cntToday = completed.count()
    cnt7day = completed7day.count()
    cnt28day = completed28day.count()
    return render_template('home.html', todoworkorder= todoworkorder, processing=processing, completed=completed,cntToday=cntToday,cnt7day=cnt7day,cnt28day=cnt28day)

@main.route('/TakeOneComputer/<id>', methods=['GET', 'POST'])
@login_required
def TakeOneComputer(id): 
    workorder = WorkOrder.query.get(id)
    workorder.status=0
    workorder.asid=current_user.id;
    workorder.astime=datetime.datetime.now()
    db.session.commit()
    
    flash('TakeOneComputer successfully')
    return redirect(url_for('main.display_workorders'))

@main.route('/UploadReport/<id>', methods=['GET', 'POST'])
@login_required
def UploadReport(id): 
    workorder = WorkOrder.query.get(id)
    workorder.intime=datetime.datetime.now()
    form = UploadReportForm(obj=workorder)
    if form.validate_on_submit():
        workorder.status = 1
        transaction = Production(wo=form.wo.data, pn=form.pn.data, csn=form.csn.data, msn=form.msn.data, cpu=form.cpu.data, 
        mem1=form.mem1.data, mem2=form.mem2.data, mem3=form.mem3.data, mem4=form.mem4.data, gpu1=form.gpu1.data, gpu2=form.gpu2.data, sata1=form.sata1.data, sata2=form.sata2.data,
        sata3=form.sata3.data, sata4=form.sata4.data, m21=form.m21.data, m22=form.m22.data, wifi=form.wifi.data, fg5g=form.fg5g.data,
        can=form.can.data,other=form.other.data,note=form.note.data,report=form.report.data)
        db.session.add(transaction)
        db.session.commit()
        flash('Upload successful')
        return redirect(url_for('main.display_workorders'))
    return render_template('uploadreport.html', form=form, id=id)

@main.route('/ReviewReport/<id>', methods=['GET', 'POST'])
@login_required
def ReviewReport(id):
        workorder = WorkOrder.query.get(id)
        products = Production.query.filter_by(wo=workorder.wo,csn=workorder.csn.strip())
        form = ReviewReportForm(obj=workorder)
        if products.count()>0 :
            product = products[0]
            form.cpu.data = product.cpu
            form.msn.data = product.msn
            form.report.data = product.report   
        workorder.intime=datetime.datetime.now()
        if form.validate_on_submit():
            if(form.action.data==0) :
               workorder.status = 2
            else :
               workorder.status = 0  
            db.session.commit()
            if(form.action.data==0) :
               flash('Confirmed')
            else :
               flash('Denied')
            return redirect(url_for('main.display_workorders'))
        return render_template('reviewreport.html', form=form, id=id)


@main.route('/ReturnOneComputer/<id>', methods=['GET', 'POST'])
@login_required
def ReturnOneComputer(id): 
    workorder = WorkOrder.query.get(id)
    workorder.status=-1
    workorder.asid=-1;
    workorder.astime=None
    db.session.commit()
    
    flash('ReturnOneComputer successfully')
    return redirect(url_for('main.display_workorders'))    

@main.route('/register/workorder', methods=['GET', 'POST'])
@login_required
def add_workorder():
    form = AddWorkorderForm()
    if form.validate_on_submit():
        csn_m=form.csn.data.split('\n')
        for x in csn_m:
           transaction = WorkOrder(wo=form.wo.data, customers=form.customers.data, pn=str(form.pn.data), csn=x.strip(), asid=-1,insid=-1,astime=None,intime=None,status=-1)
           db.session.add(transaction)
        db.session.commit()
        flash('WorkOrder registered successfully')
        return redirect(url_for('main.display_workorders'))
    return render_template('add_workorder.html', form=form)


@main.route('/add/transaction', methods=['GET', 'POST'])
@login_required
def add_transaction():
    transaction=WorkOrder.query.filter_by(status = -1)
    form = EditWorkOrderForm(obj=transaction)
    if form.validate_on_submit():
        personname_m=form.person_name.data.split('\n')
        #transaction = Transaction(type=form.type.data, asset_name=str(form.asset_name.data), person_name=form.person_name.data,
        #            start_time=form.start_time.data, end_time=None, status=form.status.data)
        for x in personname_m:
           transaction = Transaction(type=form.type.data, asset_name=str(form.asset_name.data), person_name=x,start_time=form.start_time.data, end_time=None, status=form.status.data)
           db.session.add(transaction)

        db.session.commit()
        flash('Asset added successfully')
        return redirect(url_for('main.display_workorders'))
    return render_template('add_transaction.html', form=form)
