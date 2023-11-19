from flask_login import login_required
from app.asset.forms import AddWorkorderForm, UploadReportForm, ReviewReportForm, ReviewReportFileForm,EditOneComputerForm
from app.asset import main
from app.asset.models import Transaction, WorkOrder, Production
from flask import render_template, flash, request, redirect, url_for
from app import db
#Dennis
#workorder status, unassigned -1, processing 0, waiting for inspection 1 finished 2.
from flask_login import current_user
import datetime
from sqlalchemy import func
from app.auth.forms  import get_userrole, get_usersname, get_useridbyname, get_username

@main.route('/')
@login_required
def display_workorders():
    role = get_userrole(current_user.id)
    if role == 0 :
        todoworkorder1 = WorkOrder.query.filter_by(status=-1,asid=-1)
        todoworkorder2 = WorkOrder.query.filter_by(status=-1,asid=current_user.id)
        todoworkorder  = todoworkorder1.union(todoworkorder2)
    else :
        todoworkorder = WorkOrder.query.filter_by(status=-1)  
    if role == 0 :
        query1 = WorkOrder.query.filter_by(asid=current_user.id, status=0)
        query2 =  WorkOrder.query.filter_by(asid=current_user.id, status=1)
    else :
        query1 = WorkOrder.query.filter_by(status=0)
        query2 =  WorkOrder.query.filter_by(status=1)
    processing = query1.union(query2)
    if role == 0 :
        completed = WorkOrder.query.filter(func.DATE(WorkOrder.intime) == func.DATE(datetime.datetime.today()),WorkOrder.asid==current_user.id,WorkOrder.status == 2)
        completed7day = WorkOrder.query.filter((func.DATE(WorkOrder.intime)) >= (func.DATE(datetime.datetime.today())-7),WorkOrder.asid==current_user.id,WorkOrder.status == 2)
        completed28day = WorkOrder.query.filter((func.DATE(WorkOrder.intime)) >= (func.DATE(datetime.datetime.today())-28),WorkOrder.asid==current_user.id,WorkOrder.status == 2)
    else :
        completed = WorkOrder.query.filter(func.DATE(WorkOrder.intime) == func.DATE(datetime.datetime.today()),WorkOrder.status == 2)
        completed7day = WorkOrder.query.filter((func.DATE(WorkOrder.intime)) >= (func.DATE(datetime.datetime.today())-7),WorkOrder.status == 2)
        completed28day = WorkOrder.query.filter((func.DATE(WorkOrder.intime)) >= (func.DATE(datetime.datetime.today())-28),WorkOrder.status == 2)
    cntToday = completed.count()
    cnt7day = completed7day.count()
    cnt28day = completed28day.count()
    return render_template('home.html', todoworkorder= todoworkorder, processing=processing, completed=completed,cntToday=cntToday,
                          cnt7day=cnt7day,cnt28day=cnt28day,userrole=role)

@main.route('/TakeOneComputer/<id>', methods=['GET', 'POST'])
@login_required
def TakeOneComputer(id): 
    workorder = WorkOrder.query.get(id)
    workorder.status=0
    workorder.asid=current_user.id
    workorder.astime=datetime.datetime.now()
    db.session.commit()
    
    flash('TakeOneComputer successfully')
    return redirect(url_for('main.display_workorders'))

@main.route('/DeleteOneComputer/<id>', methods=['GET', 'POST'])
@login_required
def DeleteOneComputer(id): 
    workorder = WorkOrder.query.get(id)
    db.session.delete(workorder)
    db.session.commit()
    flash('DeleteOneComputer successfully')
    return redirect(url_for('main.display_workorders'))

@main.route('/EditOneComputer/<id>', methods=['GET', 'POST'])
@login_required
def EditOneComputer(id): 
    workorder = WorkOrder.query.get(id)
    form = EditOneComputerForm(obj=workorder)
    role = get_userrole(current_user.id)
    if form.validate_on_submit():
        print(form.cpuinstall.data)
        workorder.wo=form.wo.data
        workorder.customers=form.customers.data
        workorder.pn=str(form.pn.data)
        workorder.csn=form.csn.data.strip()
        workorder.cpuinstall = form.cpuinstall.data
        workorder.memoryinstall = form.memoryinstall.data
        workorder.gpuinstall = form.gpuinstall.data
        workorder.wifiinstall = form.wifiinstall.data
        workorder.mezioinstall = form.mezioinstall.data
        workorder.caninstall = form.caninstall.data
        workorder.osinstall = form.osinstall.data
        if form.operator.data == None :
            asidset =-1
        else :
            asidset = form.operator.data.id
        workorder.asid = asidset    
        db.session.commit()
        flash('Update successful')
        return redirect(url_for('main.display_workorders'))
    return render_template('edit_OneComputer.html', form=form, id=id, userrole=role) 

@main.route('/UploadReport/<id>', methods=['GET', 'POST'])
@login_required
def UploadReport(id): 
    workorder = WorkOrder.query.get(id)
    workorder.intime=datetime.datetime.now()
    form = UploadReportForm(obj=workorder)
    role = get_userrole(current_user.id)
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
    return render_template('uploadreport.html', form=form, id=id,userrole = role)

@main.route('/ReviewReport/<id>', methods=['GET', 'POST'])
@login_required
def ReviewReport(id):
        workorder = WorkOrder.query.get(id)
        products = Production.query.filter_by(wo=workorder.wo,csn=workorder.csn.strip())
        form = ReviewReportForm(obj=workorder)
        role = get_userrole(current_user.id)
        if products.count()>0 :
            product = products[0]
            form.cpu.data = product.cpu
            form.msn.data = product.msn
            form.report.data = product.report   
            form.mem1.data = product.mem1
            form.mem2.data = product.mem2
            form.mem3.data = product.mem3
            form.mem4.data = product.mem4
            form.gpu1.data = product.gpu1
            form.gpu2.data = product.gpu2
            form.sata1.data= product.sata1
            form.sata2.data= product.sata2
            form.sata3.data= product.sata3
            form.sata4.data= product.sata4
            form.m21.data= product.m21
            form.m22.data= product.m22
            form.wifi.data=product.wifi
            form.fg5g.data=product.fg5g
            form.can.data =product.can
            form.other.data=product.other
            form.note.data=product.note
        workorder.intime=datetime.datetime.now()
        if form.validate_on_submit():
            print(form.action.data)
            if form.action.data == '0' :
                workorder.status = 2
                print("it0")
            else: 
                workorder.status = 0  
                print("it1")
            print(workorder.status)
            db.session.commit()
            if(form.action.data=='0') :
               flash('Approved')
            else :
               flash('Denied')
            return redirect(url_for('main.display_workorders'))
        return render_template('reviewreport.html', form=form, id=id, userrole = role)


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
    role = get_userrole(current_user.id)
    if form.validate_on_submit():
        if form.operator.data == None :
            asidset =-1
        else :
            asidset = form.operator.data.id   
        csn_m=form.csn.data.split('\n')
        for x in csn_m:
            if x.strip() != '' :
                transaction = WorkOrder(wo=form.wo.data, customers=form.customers.data, pn=str(form.pn.data), csn=x.strip(), 
                cpuinstall=form.cpuinstall.data,memoryinstall=form.memoryinstall.data,gpuinstall=form.gpuinstall.data,
                wifiinstall=form.wifiinstall.data,mezioinstall=form.mezioinstall.data,caninstall=form.caninstall.data,
                osinstall=form.osinstall.data,asid=asidset,insid=-1,astime=None,intime=None,status=-1)
                db.session.add(transaction)
        db.session.commit()
        flash('WorkOrder registered successfully')
        return redirect(url_for('main.display_workorders'))
    return render_template('add_workorder.html', form=form, userrole = role)



