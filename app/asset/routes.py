import os, subprocess, csv, io, re
from flask_login import login_required
from app.asset.forms import AddWorkorderForm, UploadReportForm, ReviewReportForm, ReviewReportFileForm,EditOneComputerForm,ReportSearchForm,QueryForm,ViewReportForm,ReviewOneComputerForm
from app.asset.forms import AddProductForm,QueryProductsForm,EditProductForm,QueryWorkordersForm,PackingCalculateForm
from app.asset.forms import QueryQlogForm,AddQualityLogForm,EditQualityLogForm
from app.asset import main
from app.asset.models import WorkOrder, Production, PnMap, PackageBox, QualityLog, RmaCases, RmaVendorShipment, RmaParts, PartsInventory

def lookup_pn(pn):
    """Lookup PN in PnMap, trying exact match first, then stripping common suffixes."""
    if not pn:
        return None
    result = PnMap.query.filter_by(pn=pn).first()
    if result:
        return result
    # Try stripping common suffixes
    import re
    suffixes = ['-UL', '-EA', '-RH01', '-RH02', '-CF1', '-CF2', '-CF3', '-KS1', '-KS-CF1',
                '-MEZ-KS-CF1-PA', '-IOT-KS-CF1-PA', '-UL-KS1', '-UL-KS1(EA)',
                '-LME', '-ADV', '-IGN', '-PoE', '-10G', '-AGX32G-COOLIT',
                '-JAO32G', '-JAO64G', '-JXI64G']
    for suffix in suffixes:
        stripped = pn
        while stripped.endswith(suffix):
            stripped = stripped[:-len(suffix)]
        if stripped and stripped != pn:
            result = PnMap.query.filter_by(pn=stripped).first()
            if result:
                return result
    # Try removing trailing parenthetical like (EA)
    cleaned = re.sub(r'\([^)]*\)', '', pn).strip()
    if cleaned != pn:
        result = PnMap.query.filter_by(pn=cleaned).first()
        if result:
            return result
    return None
from flask import render_template, flash, request, redirect, url_for, session, send_from_directory, Response, abort
from app import db
from app.asset.forms import get_biosversion, get_sopversion

#Dennis
#workorder status, unassigned -1, processing 0, waiting for inspection 1 finished 2.
from flask_login import current_user
import datetime
from sqlalchemy import func, or_
from app.auth.forms  import get_userrole, get_usersname, get_useridbyname, get_username
from app.auth.models import User
import math
from werkzeug.utils import secure_filename
from docx import Document
import os,docx
from app.asset.packing import Package,Box,classifier   #packing calculate
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSION = {'doc','docx'}
#cputype            null or CPU type 
#memorysize         null or memory size
#disksize           null or disk size
#cpuinstall         True or False, use for score  
#memoryinstall      True or False, use for score  
#gpuinstall         True or False, use for score 
#wifiinstall        True or False, use for score 
#caninstall         True or False, use for score 
#mezioinstall       True or False, use for score 
#fg5ginstall        True or False, use for score 
#osinstall          null or OS name, use for score 
#gpu                True or False or null, use for workorder auto check and score 
#withwifi           True or False or null, use for workorder auto check  
#withcan            True or False or null, use for workorder auto check 
#withfg5g           True or False or null, use for workorder auto check 
#ospreinstalled     True or False or null
#diskpreinstalled   True or False or null
#install cpu,memory or disk\
def testonly(unit): 
    if unit.cpuinstall or unit.memoryinstall or (unit.diskpreinstalled == False) :
        return  False 
    else :    
        return  True
def CalculateUnitBuildScore(unit,basicscoreinfo):
    BuildScore=0
    #basicscoreinfo = PnMap.query.filter(PnMap.id!=0)
    # Will not count RMA case        
    if "RNTA" not in unit.wo:
        if unit.packgo != True :
            unitscoreinfo  = basicscoreinfo.filter_by(pn=unit.pn)
            unitbuild    = 6
            unittestonly = 3
            unitgpu      = 0
            unitextra = 0    
            if unitscoreinfo.count() :
                unittestonly = unitscoreinfo[0].testonlypoints
                unitbuild    = unitscoreinfo[0].buildpoints
                unitgpu      = unitscoreinfo[0].gpu
                unitextra    = unitscoreinfo[0].extra  
                maxunitinabox= unitscoreinfo[0].unitsinabox  
                # NRU ? NX ? PCIe ? IGT ? FLYC?
                # NRU-154/156            6/3
                # PCIe-NX154/PCIe-NX156  6/3
            elif "NRU-154" in unit.pn or "NRU-156" in unit.pn\
                    or "IGT-" in unit.pn or "FLYC" in unit.pn\
                    or "PCIe-NX154" in unit.pn or "PCIe-NX156" in unit.pn : 
                unitbuild    = 6
                unittestonly = 3
                # NRU-51V/51V+ 52S/52S+  7/3
            elif "NRU-51V" in unit.pn or "NRU-52S" in unit.pn :
                unitbuild    = 7
                unittestonly = 3
                # NRU-110V/120S/220S     8/4
            elif "NRU-110V" in unit.pn or "NRU-120S" in unit.pn\
                    or "NRU-220S" in unit.pn :
                unitbuild    = 8
                unittestonly = 4
                # NRU-222S/230V/240AWP   8/5
            elif "NRU-222S" in unit.pn or "NRU-230V" in unit.pn\
                    or "NRU-240S" in unit.pn :
                unitbuild    = 8
                unittestonly = 5

            if testonly(unit) :
                BuildScore = BuildScore + unittestonly
                #check disk installation     
                if unit.diskpreinstalled != True and len(unit.memorysize.strip()):
                    BuildScore = BuildScore + 2 
            else :
                BuildScore = BuildScore + unitbuild
            #check OS installation 
            if unit.ospreinstalled != True and len(unit.osinstall.strip()):
                BuildScore = BuildScore + 1
            #check OS activiation 
            if unit.osactivation != True and len(unit.osinstall.strip()):
                BuildScore = BuildScore + 0.5
            #check Wifi installation 
            if unit.wifiinstall == True:
                BuildScore = BuildScore + 0.5
            #check can installation 
            if unit.caninstall == True:
                BuildScore = BuildScore + 0.5
            #check mezio installation 
            if unit.mezioinstall == True :
                BuildScore = BuildScore + 0.25
            #check fg5g installation 
            if unit.fg5ginstall == True:
                BuildScore = BuildScore + 1
            #check gpu install
            if unit.gpuinstall == True :
                BuildScore = BuildScore + unitgpu  
            BuildScore = BuildScore + unitextra
    return BuildScore

def CalculateScore(completed,basicscoreinfo):
   #2026/7/6-2026/7/13 Daniel, SuplyCore , pack & go hybrid workorder, calculate error  
    BuildScore=0
    PackScore =0
    #basicscoreinfo = PnMap.query.filter(PnMap.id!=0)
    completed = completed.order_by(WorkOrder.wo)
    lastwo = ""
    cntinwo= 0.0
    #PCIe card,IGT,FLYC-300
    maxunitinabox = 25 
    #calculate build and test score
    for unit in completed :
        #not count rma CASE
        if unit.wo != lastwo :
            #calculate pack score
            if cntinwo!= 0 :
                PackScore = PackScore + math.ceil( cntinwo / maxunitinabox)*2
                lastwo = unit.wo
                cntinwo= 0.0
                maxunitinabox = 25
        # Will not count RMA case        
        if "RNTA" not in unit.wo:
            #first unit in current wo
            #if cntinwo == 0:
            unitscoreinfo  = basicscoreinfo.filter_by(pn=unit.pn)
            #default value
            unitbuild = 6
            unittestonly = 3
            unitgpu = 0
            unitextra=0
            cntinwo = cntinwo + 1
            if unit.packgo == True:
               continue
            #if cntinwo == 1:
            #multiple product in one work order
            if unitscoreinfo.count() :
                unittestonly = unitscoreinfo[0].testonlypoints
                unitbuild    = unitscoreinfo[0].buildpoints
                unitgpu      = unitscoreinfo[0].gpu
                unitextra    = unitscoreinfo[0].extra 
                maxunitinabox= unitscoreinfo[0].unitsinabox  
            # NRU ? NX ? PCIe ? IGT ? FLYC?
            # NRU-154/156            6/3
            # PCIe-NX154/PCIe-NX156  6/3
            elif "NRU-154" in unit.pn or "NRU-156" in unit.pn\
                or "IGT-" in unit.pn or "FLYC" in unit.pn\
                or "PCIe-NX154" in unit.pn or "PCIe-NX156" in unit.pn : 
                unitbuild    = 6
                unittestonly = 3
                maxunitinabox= 4 
            # NRU-51V/51V+ 52S/52S+  7/3
            elif "NRU-51V" in unit.pn or "NRU-52S" in unit.pn :
                unitbuild    = 7
                unittestonly = 3
                maxunitinabox= 4 
            # NRU-110V/120S/220S     8/4
            elif "NRU-110V" in unit.pn or "NRU-120S" in unit.pn\
                or "NRU-220S" in unit.pn :
                unitbuild    = 8
                unittestonly = 4
                maxunitinabox= 4 
            # NRU-222S/230V/240AWP   8/5
            elif "NRU-222S" in unit.pn or "NRU-230V" in unit.pn\
                or "NRU-240S" in unit.pn :
                unitbuild    = 8
                unittestonly = 5
                maxunitinabox= 4 
            if testonly(unit) :
                BuildScore = BuildScore + unittestonly
                #check disk installation     
                if unit.diskpreinstalled != True and len(unit.memorysize.strip()):
                    BuildScore = BuildScore + 2 
            else :
                BuildScore = BuildScore + unitbuild
            #check OS installation 
            if unit.ospreinstalled != True and len(unit.osinstall.strip()):
                BuildScore = BuildScore + 1
            #check OS activiation 
            if unit.osactivation != True and len(unit.osinstall.strip()):
                BuildScore = BuildScore + 0.5
            #check Wifi installation 
            if unit.wifiinstall == True:
                BuildScore = BuildScore + 0.5
            #check can installation 
            if unit.caninstall == True:
                BuildScore = BuildScore + 0.5
            #check mezio installation 
            if unit.mezioinstall == True :
                BuildScore = BuildScore + 0.25
            #check fg5g installation 
            if unit.fg5ginstall == True:
                BuildScore = BuildScore + 1
            #check gpu install
            if unit.gpuinstall == True :
                BuildScore = BuildScore + unitgpu  
            BuildScore = BuildScore + unitextra
    #last wororder            
    if cntinwo!= 0 :
        PackScore = PackScore + math.ceil( cntinwo / maxunitinabox)*2
    #calculate pack score by workorder
    return (BuildScore+PackScore)

@main.route('/takemore', methods=['GET', 'POST'])
@login_required
def takemore():
    print("take more")
    x = request.json
    y = x.get("message")
    z = y.split()
    for sid in z:
        print(sid)
        workorder = WorkOrder.query.get(sid)
        workorder.status=0
        workorder.asid=current_user.id
        workorder.tktime=datetime.datetime.now()
        db.session.commit()
    return redirect(url_for('main.display_workorders'))

@main.route('/pendingmore', methods=['POST'])
@login_required
def pendingmore():
    x = request.json
    y = x.get("message")
    for sid in y.split():
        wo = WorkOrder.query.get(sid)
        wo.status = -2
        db.session.commit()
    return redirect(url_for('main.display_workorders'))
    
def packing_solution_for(id):
    wo = WorkOrder.query.get(id)
    if not wo:
        return None
    product = lookup_pn(wo.pn)
    if not product:
        return None
    result = {
        'wo': wo.wo, 'pn': wo.pn, 'csn': wo.csn,
        'internal': [], 'external': [],
        'box_name': '', 'box_dims': '',
    }
    from app.asset.packing import Box, Package, packer, classifier
    from app.asset.models import PackageBox
    boxes = PackageBox.query.filter_by(status=1).all()
    platforms = {'Platform1': [Box('Platform1', b.name, b.width, b.thickness, b.height, b.limitweight - b.weight, b.weight) for b in boxes]}
    packages = []

    # Parse doc_items (format: PNxQTY|PNxQTY|...) or use PN itself
    items_to_pack = []
    if wo.doc_items:
        for part in wo.doc_items.split('|'):
            part = part.strip()
            if not part:
                continue
            if 'x' in part:
                pn, qty = part.rsplit('x', 1)
                try:
                    qty = int(qty)
                except:
                    qty = 1
            else:
                pn, qty = part, 1
            items_to_pack.append((pn.strip(), qty))
    else:
        items_to_pack.append((wo.pn, 1))

    # Build package list: pair computers with their power adaptors
    # First, get inneraccessory of the main computer to know what fits inside
    main_comp = lookup_pn(items_to_pack[0][0]) if items_to_pack else None
    inner_acc_set = set()
    if main_comp and main_comp.inneraccessory:
        for acc_str in main_comp.inneraccessory.replace('|', ',').split(','):
            acc_str = acc_str.strip()
            if acc_str:
                inner_acc_set.add(acc_str.upper())
    computer_pkgs = []
    pa_pkgs = []
    cbl_pkgs = []
    other_pkgs = []
    inside_pkgs = []  # items that fit inside the computer box
    for pn, qty in items_to_pack:
        item = lookup_pn(pn)
        if not item:
            result['internal'].append(f"{pn} (not found in DB)")
            continue
        # Check if this item is an inneraccessory of the computer (fits inside)
        is_inner = False
        if inner_acc_set:
            for check in [pn.upper(), (item.abbreviation or '').upper()]:
                if check in inner_acc_set:
                    is_inner = True
                    break
        if is_inner:
            result['internal'].append(f"{pn} x{qty} (fits inside)")
            inside_pkgs.extend([Package(pn, 1, 1, 1, 1)] * qty)
            continue
        pkgs = []
        for _ in range(qty):
            if item.width and item.height and item.thickness:
                pkgs.append(Package(pn, item.width, item.thickness, item.height, item.weight or 1))
        if item.pn.startswith('PA-') or item.category == 'CABLEKIT':
            (pa_pkgs if item.pn.startswith('PA-') else cbl_pkgs).extend(pkgs)
            result['external'].append(f"{pn} x{qty}")
        elif not item.category or item.category in ('COMPUTER', 'NRU', 'SEMIL', 'PB', 'CARD', 'GPU'):
            computer_pkgs.extend(pkgs)
            result['internal'].append(f"{pn} x{qty}")
        else:
            other_pkgs.extend(pkgs)
            result['internal'].append(f"{pn} x{qty}")
    # Strategy: call calculator once for one set, then compare with all-items
    from app.asset.packing import Box as PackBox, Package as PackPkg, classifier
    box_objs = [PackBox('Platform1', b.name, b.width, b.thickness, b.height, b.limitweight - b.weight, b.weight) for b in boxes if b.status == 1]
    # Include special-purpose boxes (status=2) that match the main computer (e.g. SEMIL, RGS)
    if main_comp and main_comp.abbreviation:
        for keyword in ('SEMIL', 'RGS'):
            if keyword in main_comp.abbreviation:
                special_boxes = PackageBox.query.filter(PackageBox.status == 2, PackageBox.purpose.like('%' + keyword + '%')).all()
                for b in special_boxes:
                    box_objs.append(PackBox('Platform1', b.name, b.width, b.thickness, b.height, b.limitweight - b.weight, b.weight))
    platforms = {'Platform1': box_objs}

    n_units = min(len(computer_pkgs), len(pa_pkgs), len(cbl_pkgs)) if pa_pkgs and cbl_pkgs else len(computer_pkgs)
    best_pdata = None

    if n_units > 0 and len(pa_pkgs) >= n_units and len(cbl_pkgs) >= n_units and all_items:
        # Strategy A: pack one set, then repeat
        one_set = [computer_pkgs[0], pa_pkgs[0], cbl_pkgs[0]]
        sol_a, det_a, pct_a, pdata_a = classifier(platforms, one_set)
        a_ok = pdata_a and len(pdata_a) == 1  # one set fits in one box
    else:
        a_ok = False

    # Strategy B: pack all items together
    all_items = computer_pkgs + pa_pkgs + cbl_pkgs + other_pkgs
    if not all_items:
        return result
    sol_b, det_b, pct_b, pdata_b = classifier(platforms, all_items)
    b_boxes = len(pdata_b) if pdata_b else 999

    result['boxes'] = []
    # Use strategy A if it works and gives same or fewer boxes
    if a_ok and n_units <= b_boxes:
        # Repeat the single-set box for each unit
        bd = pdata_a[0]
        for i in range(n_units):
            items = []
            if i < len(computer_pkgs): items.append(computer_pkgs[i].get_name())
            if i < len(pa_pkgs): items.append(pa_pkgs[i].get_name())
            if i < len(cbl_pkgs): items.append(cbl_pkgs[i].get_name())
            result['boxes'].append({
                'name': bd['name'], 'w': bd['w'], 't': bd['t'], 'h': bd['h'],
                'packages': items,
            })
    elif pdata_b:
        for bd in pdata_b:
            box_items = [pkg['name'] for pkg in bd['packages']]
            result['boxes'].append({
                'name': bd['name'], 'w': bd['w'], 't': bd['t'], 'h': bd['h'],
                'packages': box_items,
            })
    return result

@main.route('/api/packing-solution/<int:id>', methods=['GET'])
@login_required
def api_packing_solution(id):
    data = packing_solution_for(id)
    if not data:
        return {'found': False}
    return {'found': True, 'data': data}

@main.route('/packmore', methods=['POST'])
@login_required
def packmore():
    import sys
    x = request.get_json(force=True, silent=True)
    if not x:
        print("packmore: no JSON", file=sys.stderr)
        return redirect(url_for('main.display_workorders'))
    msg = x.get("message", "")
    print(f"packmore: message={msg}", file=sys.stderr)
    count = 0
    for sid in msg.strip().split():
        wo = WorkOrder.query.get(int(sid))
        if wo and wo.status == 3:
            count += 1
            wo.status = 1
            wo.packid = current_user.id
            wo.tkforpacktime = datetime.datetime.now()
            wo.pktime = datetime.datetime.now()
            db.session.commit()
    flash(f'Packed {count} item(s)')
    return redirect(url_for('main.display_workorders'))

@main.route('/packdone', methods=['POST'])
@login_required
def packdone():
    x = request.json
    count = 0
    for sid in x.get("message", "").split():
        wo = WorkOrder.query.get(sid)
        if wo and wo.status == 4:
            wo.status = 1
            wo.pktime = datetime.datetime.now()
            db.session.commit()
            count += 1
    flash(f'Packed more {count} item(s)')
    return redirect(url_for('main.display_workorders'))

@main.route('/inspectfinal', methods=['POST'])
@login_required
def inspectfinal():
    x = request.json
    count = 0
    for sid in x.get("message", "").split():
        wo = WorkOrder.query.get(sid)
        if wo and wo.status == 5:
            wo.status = 2
            wo.finalintime = datetime.datetime.now()
            db.session.commit()
            count += 1
    flash(f'Final inspected {count} item(s)')
    return redirect(url_for('main.display_workorders'))

@main.route('/uploadmore', methods=['GET', 'POST'])
@login_required
def uploadmore():
    import sys
    print("upload more", file=sys.stderr)
    x = request.get_json(force=True, silent=True)
    if not x:
        print("uploadmore: no JSON received", file=sys.stderr)
        return redirect(url_for('main.display_workorders'))
    y = x.get("message", "")
    if not y:
        print("uploadmore: empty message", file=sys.stderr)
        return redirect(url_for('main.display_workorders'))
    z = y.strip().split()
    print(f"uploadmore: ids={z}", file=sys.stderr)
    count = 0
    skipped = 0
    for sid in z:
        print(sid, file=sys.stderr)
        workorder = WorkOrder.query.get(int(sid))
        if workorder.packgo != True:
            print(f"uploadmore: skip {sid} (not pack & go)", file=sys.stderr)
            skipped += 1
            continue
        workorder.astime=datetime.datetime.now()
        workorder.status = 3
        transaction = Production(wo=workorder.wo, pn=workorder.pn, csn=workorder.csn, msn="N/A", cpu="N/A",
            mem1="", mem2="", mem3="", mem4="", gpu1="", gpu2="",
            sata1="", sata2="",sata3="", sata4="", m21="", m22="", wifi="", fg5g="",can="",other="",note="",report="")
        existproduct = Production.query.filter_by(wo=workorder.wo,csn=workorder.csn)
        if existproduct.count() :
            db.session.delete(existproduct[0])
        db.session.add(transaction)
        db.session.commit()
        count += 1
    if skipped:
        flash(f'Uploaded {count} pack&go item(s); skipped {skipped} Build item(s) - use Upload Report for Build')
    else:
        flash(f'Uploaded {count} item(s)')
    return redirect(url_for('main.display_workorders'))

@main.route('/inspectmore', methods=['GET', 'POST'])
@login_required
def inspectmore():
    print("inspect more")
    role = get_userrole(current_user.id)
    x = request.json
    y = x.get("message")
    z = y.split()
    for sid in z:
        print(sid)
        workorder = WorkOrder.query.get(sid)
        if(workorder.packgo == True or role >= 2):
            workorder.intime=datetime.datetime.now()
            if workorder.status == 1:
                workorder.status = 2
                workorder.insid = current_user.id
            db.session.commit()
    return redirect(url_for('main.display_workorders'))    

@main.route('/dashboard')
@login_required
def dashboard():
    role = get_userrole(current_user.id)
    basicscoreinfo = PnMap.query.filter(PnMap.id!=0)
    today = datetime.datetime.today()

    def uf(query):
        if role == 0:
            return query.filter(WorkOrder.asid == current_user.id)
        return query

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    use_custom_range = start_date and end_date

    if use_custom_range:
        try:
            sd = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            ed = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        except (ValueError, TypeError):
            sd = ed = None
            use_custom_range = False

    def get_kpi(days):
        base = uf(WorkOrder.query.filter(WorkOrder.status == 2))
        if use_custom_range:
            base = base.filter(func.DATE(WorkOrder.intime) >= func.DATE(sd), func.DATE(WorkOrder.intime) <= func.DATE(ed))
        elif days == 0:
            base = base.filter(func.DATE(WorkOrder.intime) == func.DATE(today))
        else:
            base = base.filter((func.DATE(WorkOrder.intime)) >= (func.DATE(today - datetime.timedelta(days=days))))
        total = base.count()
        build = total - base.filter_by(packgo=True).count()
        barebone = base.filter(db.or_(WorkOrder.cpuinstall == True, WorkOrder.memoryinstall == True)).count()
        ins_os = build - base.filter_by(osinstall='', packgo=False).count()
        ins_module = build - base.filter_by(gpuinstall=False, wifiinstall=False, caninstall=False, mezioinstall=False, packgo=False).count()
        ins_gpu = base.filter_by(gpuinstall=True).count()
        score = CalculateScore(base.order_by(WorkOrder.wo), basicscoreinfo)
        return [total, build, ins_os, ins_module, ins_gpu, score, barebone]

    cntToday = get_kpi(0) if not use_custom_range else None
    cnt7day = get_kpi(7) if not use_custom_range else None
    cnt28day = get_kpi(28) if not use_custom_range else None
    cntCustom = get_kpi(-1) if use_custom_range else None

    # Backlog meter
    backlog = {
        'unassigned': uf(WorkOrder.query.filter_by(status=-1)).count(),
        'pending': uf(WorkOrder.query.filter_by(status=-2)).count(),
        'processing': uf(WorkOrder.query.filter_by(status=0)).count(),
        'waiting_inspection': uf(WorkOrder.query.filter_by(status=1)).count(),
        'waiting_packing': uf(WorkOrder.query.filter_by(status=3)).count(),
        'packing': uf(WorkOrder.query.filter_by(status=4)).count(),
        'waiting_final': uf(WorkOrder.query.filter_by(status=5)).count(),
        'completed_today': uf(WorkOrder.query.filter(func.DATE(WorkOrder.intime) == func.DATE(today), WorkOrder.status == 2)).count(),
    }

    # RMA Cases counts
    channel_names = ['CoastIPC', 'Aerflite', 'Industrial PC']
    def rma_counts_for(base_q):
        return {
            'new': base_q.filter_by(status='new').count(),
            'received': base_q.filter_by(status='received').count(),
            'processing': base_q.filter_by(status='processing').count(),
            'waiting_for_shipping': base_q.filter_by(status='waiting_for_shipping').count(),
            'shipped_to_vendor': base_q.filter_by(status='shipped_to_vendor').count(),
            'closed': base_q.filter_by(status='closed').count(),
            'canceled': base_q.filter_by(status='canceled').count(),
            'total': base_q.count(),
        }
    from sqlalchemy import func as sa_func
    def conclusions_for(base_q):
        return db.session.query(RmaCases.conclusion, sa_func.count(RmaCases.id)).filter(
            RmaCases.id.in_(base_q.with_entities(RmaCases.id).subquery()),
            RmaCases.status == 'closed', RmaCases.conclusion != None, RmaCases.conclusion != ''
        ).group_by(RmaCases.conclusion).order_by(sa_func.count(RmaCases.id).desc()).all()

    all_q = RmaCases.query
    retail_q = RmaCases.query
    channel_q = RmaCases.query.filter(db.or_(*[RmaCases.customers.ilike(f'%{c}%') for c in channel_names]))
    for c in channel_names:
        retail_q = retail_q.filter(~RmaCases.customers.ilike(f'%{c}%'))

    def flat_conc(rows):
        return [[str(r[0]), int(r[1])] for r in rows]
    def iw_oow(base_q):
        iw = oow = 0
        for c in base_q.filter_by(status='closed').all():
            w = (c.warranty or '').strip().lower()
            if w in ('yes',) or '-' in w or '/' in w:
                iw += 1
            else:
                oow += 1
        return iw, oow
    rma_counts_val = rma_counts_for(all_q)
    rma_counts_val['conclusions'] = flat_conc(conclusions_for(all_q))
    rma_counts_val['iw'], rma_counts_val['oow'] = iw_oow(all_q)
    closed_rows = db.session.query(RmaCases.processid, sa_func.count(RmaCases.id)).filter(
        RmaCases.status == 'closed', RmaCases.processid != None
    ).group_by(RmaCases.processid).order_by(sa_func.count(RmaCases.id).desc()).all()
    rma_counts_val['closed_notes'] = [
        {'count': int(cnt), 'processby': get_username(pid) if pid else ''}
        for pid, cnt in closed_rows
    ]
    rma_retail_val = rma_counts_for(retail_q)
    rma_retail_val['conclusions'] = flat_conc(conclusions_for(retail_q))
    rma_retail_val['iw'], rma_retail_val['oow'] = iw_oow(retail_q)
    rma_channel_val = rma_counts_for(channel_q)
    rma_channel_val['conclusions'] = flat_conc(conclusions_for(channel_q))
    rma_channel_val['iw'], rma_channel_val['oow'] = iw_oow(channel_q)

    # RMA Rate & DOA Rate: retail only, quarterly
    computer_prefixes = ('NRU', 'Nuvo', 'SEMIL', 'GT', 'FLYC', 'PCIe', 'POC')
    rma_quarters = []
    doa_quarters = []
    q_start = datetime.datetime(2026, 1, 1)
    last_complete = datetime.datetime(today.year, ((today.month - 1) // 3) * 3 + 1, 1)
    # Pre-compute 2025-Q4 build for DOA rate denominator of 2026-Q1
    prev_start = q_start - datetime.timedelta(days=95)
    prev_q = WorkOrder.query.filter(
        WorkOrder.intime >= prev_start, WorkOrder.intime < q_start,
        WorkOrder.status == 2,
        db.or_(*[WorkOrder.pn.like(f'{p}%') for p in computer_prefixes]),
        db.or_(WorkOrder.cpuinstall == True, WorkOrder.memoryinstall == True, WorkOrder.packgo == True),
    )
    for c in channel_names:
        prev_q = prev_q.filter(~WorkOrder.customers.ilike(f'%{c}%'))
    prev_denom = prev_q.count()
    while q_start < last_complete:
        q_end = q_start + datetime.timedelta(days=93)
        if q_end > today:
            q_end = today
        # Build computers this quarter
        wo_q = WorkOrder.query.filter(
            WorkOrder.intime >= q_start, WorkOrder.intime < q_end,
            WorkOrder.status == 2,
            db.or_(*[WorkOrder.pn.like(f'{p}%') for p in computer_prefixes]),
            db.or_(WorkOrder.cpuinstall == True, WorkOrder.memoryinstall == True, WorkOrder.packgo == True),
        )
        for c in channel_names:
            wo_q = wo_q.filter(~WorkOrder.customers.ilike(f'%{c}%'))
        denom = wo_q.count()
        qnum = (q_start.month - 1) // 3 + 1
        label = f"{q_start.year}-Q{qnum}"

        # RMA numerator: in-warranty retail closed cases
        rma_q = RmaCases.query.filter(
            RmaCases.cstime >= q_start, RmaCases.cstime < q_end,
            RmaCases.status == 'closed',
            ~RmaCases.conclusion.ilike('%No Problem Found%'),
            ~RmaCases.rmatype.ilike('ECN'),
        )
        for c in channel_names:
            rma_q = rma_q.filter(~RmaCases.customers.ilike(f'%{c}%'))
        rma_q = rma_q.filter(~RmaCases.customers.ilike('NTA'))
        numer = 0
        for c in rma_q.all():
            w = (c.warranty or '').strip().lower()
            if w in ('yes',) or '-' in w or '/' in w:
                numer += 1
        rma_quarters.append({
            'label': label, 'numer': numer, 'denom': denom,
            'rate': round(numer / denom * 100, 2) if denom else 0,
        })

        # DOA numerator: DOA cases this quarter, with prev quarter build as denominator
        doa_q = RmaCases.query.filter(
            RmaCases.cstime >= q_start, RmaCases.cstime < q_end,
            RmaCases.rmatype == 'DOA',
        )
        for c in channel_names:
            doa_q = doa_q.filter(~RmaCases.customers.ilike(f'%{c}%'))
        doa_q = doa_q.filter(~RmaCases.customers.ilike('NTA'))
        doa_cnt = doa_q.count()
        doa_quarters.append({
            'label': label, 'numer': doa_cnt, 'denom': prev_denom,
            'rate': round(doa_cnt / prev_denom * 100, 2) if prev_denom else 0,
        })
        prev_denom = denom
        q_start = q_end
    rma_rate_data = rma_quarters
    doa_rate_data = doa_quarters

    # Monthly RMA & DOA rates for the current (partial) quarter
    def _month_build(s, e):
        q = WorkOrder.query.filter(
            WorkOrder.intime >= s, WorkOrder.intime < e,
            WorkOrder.status == 2,
            db.or_(*[WorkOrder.pn.like(f'{p}%') for p in computer_prefixes]),
            db.or_(WorkOrder.cpuinstall == True, WorkOrder.memoryinstall == True, WorkOrder.packgo == True),
        )
        for c in channel_names:
            q = q.filter(~WorkOrder.customers.ilike(f'%{c}%'))
        return q.count()

    def _prev_month_avg(y, mo, k):
        counts = []
        for back in range(1, k + 1):
            yy, mm = y, mo
            for _ in range(back):
                mm -= 1
                if mm == 0:
                    mm = 12
                    yy -= 1
            ps = datetime.datetime(yy, mm, 1)
            pey, pem = (yy + 1, 1) if mm == 12 else (yy, mm + 1)
            pe = datetime.datetime(pey, pem, 1)
            counts.append(_month_build(ps, pe))
        return round(sum(counts) / len(counts), 2) if counts else 0

    rma_months = []
    doa_months = []
    m = datetime.datetime(last_complete.year, last_complete.month, 1)
    today_mid = datetime.datetime(today.year, today.month, today.day)
    while m < today_mid + datetime.timedelta(days=1):
        ny, nm = (m.year + 1, 1) if m.month == 12 else (m.year, m.month + 1)
        m_end = datetime.datetime(ny, nm, 1)
        if m_end > today_mid:
            m_end = today_mid + datetime.timedelta(days=1)
        denom_m = _month_build(m, m_end)
        rma_m = RmaCases.query.filter(
            RmaCases.cstime >= m, RmaCases.cstime < m_end,
            RmaCases.status == 'closed',
            ~RmaCases.conclusion.ilike('%No Problem Found%'),
            ~RmaCases.rmatype.ilike('ECN'),
        )
        for c in channel_names:
            rma_m = rma_m.filter(~RmaCases.customers.ilike(f'%{c}%'))
        rma_m = rma_m.filter(~RmaCases.customers.ilike('NTA'))
        numer_m = 0
        for c in rma_m.all():
            w = (c.warranty or '').strip().lower()
            if w in ('yes',) or '-' in w or '/' in w:
                numer_m += 1
        doa_m = RmaCases.query.filter(
            RmaCases.cstime >= m, RmaCases.cstime < m_end,
            RmaCases.rmatype == 'DOA',
        )
        for c in channel_names:
            doa_m = doa_m.filter(~RmaCases.customers.ilike(f'%{c}%'))
        doa_m = doa_m.filter(~RmaCases.customers.ilike('NTA'))
        doa_cnt_m = doa_m.count()
        doa_denom = _prev_month_avg(m.year, m.month, 3)
        mlabel = f"{m.year}-{m.month:02d}"
        rma_months.append({
            'label': mlabel, 'numer': numer_m, 'denom': denom_m,
            'rate': round(numer_m / denom_m * 100, 2) if denom_m else 0,
        })
        doa_months.append({
            'label': mlabel, 'numer': doa_cnt_m, 'denom': doa_denom,
            'rate': round(doa_cnt_m / doa_denom * 100, 2) if doa_denom else 0,
        })
        m = m_end

    # RMA process efficiency: of all cases received in a month, % closed within 15 work days (receive->close), monthly since 2026-01-01
    def _workdays(a, b):
        d = a.date() + datetime.timedelta(days=1)
        end = b.date()
        cnt = 0
        while d <= end:
            if d.weekday() < 5:
                cnt += 1
            d += datetime.timedelta(days=1)
        return cnt

    rma_eff_iw = []
    rma_eff_oow = []
    em = datetime.datetime(2026, 1, 1)
    em_max = today_mid + datetime.timedelta(days=1)
    while em < em_max:
        ey, emn = (em.year + 1, 1) if em.month == 12 else (em.year, em.month + 1)
        em_end = datetime.datetime(ey, emn, 1)
        if em_end > em_max:
            em_end = em_max
        eff_q = RmaCases.query.filter(
            RmaCases.recvtime >= em, RmaCases.recvtime < em_end,
        )
        eff_q = eff_q.filter(~RmaCases.customers.ilike('NTA'))
        eff_cases = eff_q.all()
        iw_total = 0
        iw_on = 0
        oow_total = 0
        oow_on = 0
        for c in eff_cases:
            w = (c.warranty or '').strip().lower()
            is_iw = (w in ('yes',)) or ('-' in w) or ('/' in w)
            closed_on_time = c.closetime and c.recvtime and _workdays(c.recvtime, c.closetime) <= 15
            if is_iw:
                iw_total += 1
                if closed_on_time:
                    iw_on += 1
            else:
                oow_total += 1
                if closed_on_time:
                    oow_on += 1
        rma_eff_iw.append({
            'label': f"{em.year}-{em.month:02d}",
            'total': iw_total, 'ontime': iw_on,
            'rate': round(iw_on / iw_total * 100, 2) if iw_total else 100,
        })
        rma_eff_oow.append({
            'label': f"{em.year}-{em.month:02d}",
            'total': oow_total, 'ontime': oow_on,
            'rate': round(oow_on / oow_total * 100, 2) if oow_total else 100,
        })
        em = em_end

    # Operator ranking
    rank_period_days = 7
    if use_custom_range:
        rank_period_days = (ed - sd).days or 1
    completed_rank = uf(WorkOrder.query.filter(
        (func.DATE(WorkOrder.intime)) >= (func.DATE(today - datetime.timedelta(days=rank_period_days))),
        WorkOrder.status == 2)) if not use_custom_range else \
        uf(WorkOrder.query.filter(func.DATE(WorkOrder.intime) >= func.DATE(sd),
                                  func.DATE(WorkOrder.intime) <= func.DATE(ed),
                                  WorkOrder.status == 2))
    ranking = []
    for user in User.query.all():
        if user.role < 3:
            user_completed = completed_rank.filter(WorkOrder.asid == user.id)
            cnt = user_completed.count()
            if cnt:
                score = CalculateScore(user_completed.order_by(WorkOrder.wo), basicscoreinfo)
                ranking.append({'id': user.id, 'name': user.user_name, 'count': cnt, 'score': score})
    ranking.sort(key=lambda r: r['score'], reverse=True)

    # Trend data with auto-aggregation based on period length
    trend_days = request.args.get('trend_days', '7')
    trend_days = 28 if trend_days == '28' else 7
    if use_custom_range:
        delta = (ed - sd).days
        trend_period = delta
    else:
        trend_period = trend_days

    def compute_day_q(day):
        q = WorkOrder.query.filter(func.DATE(WorkOrder.intime) == func.DATE(day), WorkOrder.status == 2)
        q = uf(q)
        total = q.count()
        pg_rows = q.filter(WorkOrder.packgo == True).count()
        wo = q.filter(or_(WorkOrder.wo.like('SO-%'), WorkOrder.wo.like('RWK%'))).with_entities(WorkOrder.wo).distinct().count()
        pg = q.filter(or_(WorkOrder.wo.like('SO-%'), WorkOrder.wo.like('RWK%')), WorkOrder.packgo == True).with_entities(WorkOrder.wo).distinct().count()
        rma = q.filter(WorkOrder.wo.like('RNTA%')).with_entities(WorkOrder.wo).distinct().count()
        return {'total': total, 'build': total - pg_rows, 'wo': wo, 'pg': pg, 'rma': rma}

    def op_key(d, period_days):
        if period_days < 14:
            return d.strftime('%m/%d')
        elif period_days < 60:
            return d.strftime('%Y-W%V')
        elif period_days < 180:
            return d.strftime('%Y-%m')
        elif period_days < 360:
            return f"{d.year} Q{(d.month-1)//3+1}"
        elif period_days < 720:
            return f"{d.year}-H{'1' if d.month <= 6 else '2'}"
        else:
            return d.strftime('%Y')

    def build_aggregated(period_days, end_day):
        from collections import OrderedDict
        buckets = OrderedDict()
        for i in range(period_days, -1, -1):
            day = end_day - datetime.timedelta(days=i)
            vals = compute_day_q(day)
            k = op_key(day, period_days)
            if k not in buckets:
                buckets[k] = {'total': 0, 'build': 0, 'wo': 0, 'pg': 0, 'rma': 0}
            for s in ('total', 'build', 'wo', 'pg', 'rma'):
                buckets[k][s] += vals[s]
        labels = list(buckets.keys())
        trend_list = [{'date': k, 'count': buckets[k]['build']} for k in labels]
        wo_list = [buckets[k]['wo'] for k in labels]
        pg_list = [buckets[k]['pg'] for k in labels]
        rma_list = [buckets[k]['rma'] for k in labels]
        build_list = [buckets[k]['build'] for k in labels]
        total_list = [buckets[k]['total'] for k in labels]
        agg_label = 'Daily' if period_days < 14 else 'Weekly' if period_days < 60 else 'Monthly' if period_days < 180 else 'Quarterly' if period_days < 360 else 'Half-Yearly' if period_days < 720 else 'Yearly'
        return trend_list, wo_list, pg_list, rma_list, build_list, total_list, agg_label, labels

    trend, wo_data, pg_data, rma_data, build_data, total_data, trend_label, trend_labels7 = build_aggregated(trend_period, ed if use_custom_range else today)
    trend28, wo_data28, pg_data28, rma_data28, build_data28, total_data28, trend_label28, trend_labels28 = build_aggregated(28, today)

    def compute_operator_daily(period_days, end_day, labels):
        """Per-operator daily totals aggregated to match labels.
           Returns dict with keys 'total','build','wo','pg','rma', each a dict of op_id -> [counts per bucket]."""
        from collections import OrderedDict, defaultdict
        start_day = end_day - datetime.timedelta(days=period_days)
        q = WorkOrder.query.filter(
            WorkOrder.status == 2,
            func.DATE(WorkOrder.intime) >= func.DATE(start_day),
            func.DATE(WorkOrder.intime) <= func.DATE(end_day),
        )
        q = uf(q)
        rows = q.with_entities(
            func.DATE(WorkOrder.intime).label('day'),
            WorkOrder.asid,
            WorkOrder.wo,
            WorkOrder.packgo
        ).all()
        op_day_counts = defaultdict(lambda: {'total': 0, 'build': 0, 'wo': set(), 'pg': set(), 'rma': set()})
        for r in rows:
            key = (r.day, r.asid)
            op_day_counts[key]['total'] += 1
            if not r.packgo:
                op_day_counts[key]['build'] += 1
            if r.wo.startswith('SO-') or r.wo.startswith('RWK'):
                op_day_counts[key]['wo'].add(r.wo)
                if r.packgo:
                    op_day_counts[key]['pg'].add(r.wo)
            elif r.wo.startswith('RNTA'):
                op_day_counts[key]['rma'].add(r.wo)
        op_ids = set(asid for (_, asid) in op_day_counts)
        result = {'total': {}, 'build': {}, 'wo': {}, 'pg': {}, 'rma': {}}
        for sid in op_ids:
            sid_str = str(sid)
            for s in ('total', 'build', 'wo', 'pg', 'rma'):
                bucket_vals = OrderedDict()
                for i in range(period_days, -1, -1):
                    day = (end_day - datetime.timedelta(days=i)).date()
                    k = op_key(end_day - datetime.timedelta(days=i), period_days)
                    entry = op_day_counts.get((day, sid), {})
                    if s in ('total', 'build'):
                        cnt = entry.get(s, 0)
                    else:
                        cnt = len(entry.get(s, set()))
                    bucket_vals[k] = bucket_vals.get(k, 0) + cnt
                result[s][sid_str] = [bucket_vals.get(l, 0) for l in labels]
        return result

    wo_total = sum(wo_data)
    pg_total = sum(pg_data)
    rma_total = sum(rma_data)
    wo_total28 = sum(wo_data28)
    pg_total28 = sum(pg_data28)
    rma_total28 = sum(rma_data28)

    op_data = compute_operator_daily(trend_period, ed if use_custom_range else today, trend_labels7)
    op_data28 = compute_operator_daily(28, today, trend_labels28)
    operator_trends = op_data['total']
    operator_build = op_data['build']
    operator_wo = op_data['wo']
    operator_pg = op_data['pg']
    operator_rma = op_data['rma']
    operator_trends28 = op_data28['total']
    operator_build28 = op_data28['build']
    operator_wo28 = op_data28['wo']
    operator_pg28 = op_data28['pg']
    operator_rma28 = op_data28['rma']



    # Product mix
    if use_custom_range:
        completed_mix = uf(WorkOrder.query.filter(func.DATE(WorkOrder.intime) >= func.DATE(sd),
                                                  func.DATE(WorkOrder.intime) <= func.DATE(ed),
                                                  WorkOrder.status == 2))
    else:
        completed_mix = uf(WorkOrder.query.filter((func.DATE(WorkOrder.intime)) >= (func.DATE(today - datetime.timedelta(days=7))), WorkOrder.status == 2))
    completed_mix_nopg = completed_mix.filter(WorkOrder.packgo != True)
    product_mix = {
        'NRU': completed_mix_nopg.filter(WorkOrder.pn.contains('NRU')).count() + completed_mix_nopg.filter(WorkOrder.pn.contains('FLYC')).count(),
        'POC/IGT': completed_mix_nopg.filter(WorkOrder.pn.contains('POC')).count() + completed_mix_nopg.filter(WorkOrder.pn.contains('IGT')).count(),
        'Nuvo-5/6/7': completed_mix_nopg.filter(WorkOrder.pn.contains('Nuvo-5')).count() + completed_mix_nopg.filter(WorkOrder.pn.contains('Nuvo-6')).count() + completed_mix_nopg.filter(WorkOrder.pn.contains('Nuvo-7')).count(),
        'Nuvo-8': completed_mix_nopg.filter(WorkOrder.pn.contains('Nuvo-8')).count(),
        'Nuvo-9': completed_mix_nopg.filter(WorkOrder.pn.contains('Nuvo-9')).count(),
        'Nuvo-10': completed_mix_nopg.filter(WorkOrder.pn.contains('Nuvo-10')).count(),
        'Nuvo-11': completed_mix_nopg.filter(WorkOrder.pn.contains('Nuvo-11')).count(),
        'SEMIL': completed_mix_nopg.filter(WorkOrder.pn.contains('SEMIL')).count(),
        'Others': completed_mix_nopg.filter(~WorkOrder.pn.contains('NRU'), ~WorkOrder.pn.contains('FLYC'), ~WorkOrder.pn.contains('POC'),
                    ~WorkOrder.pn.contains('IGT'), ~WorkOrder.pn.contains('Nuvo'), ~WorkOrder.pn.contains('SEMIL')).count(),
    }
    product_mix = {k: v for k, v in product_mix.items() if v > 0}

    # 28-day product mix
    completed_mix28 = uf(WorkOrder.query.filter((func.DATE(WorkOrder.intime)) >= (func.DATE(today - datetime.timedelta(days=28))), WorkOrder.status == 2))
    completed_mix28_nopg = completed_mix28.filter(WorkOrder.packgo != True)
    product_mix28 = {
        'NRU': completed_mix28_nopg.filter(WorkOrder.pn.contains('NRU')).count() + completed_mix28_nopg.filter(WorkOrder.pn.contains('FLYC')).count(),
        'POC/IGT': completed_mix28_nopg.filter(WorkOrder.pn.contains('POC')).count() + completed_mix28_nopg.filter(WorkOrder.pn.contains('IGT')).count(),
        'Nuvo-5/6/7': completed_mix28_nopg.filter(WorkOrder.pn.contains('Nuvo-5')).count() + completed_mix28_nopg.filter(WorkOrder.pn.contains('Nuvo-6')).count() + completed_mix28_nopg.filter(WorkOrder.pn.contains('Nuvo-7')).count(),
        'Nuvo-8': completed_mix28_nopg.filter(WorkOrder.pn.contains('Nuvo-8')).count(),
        'Nuvo-9': completed_mix28_nopg.filter(WorkOrder.pn.contains('Nuvo-9')).count(),
        'Nuvo-10': completed_mix28_nopg.filter(WorkOrder.pn.contains('Nuvo-10')).count(),
        'Nuvo-11': completed_mix28_nopg.filter(WorkOrder.pn.contains('Nuvo-11')).count(),
        'SEMIL': completed_mix28_nopg.filter(WorkOrder.pn.contains('SEMIL')).count(),
        'Others': completed_mix28_nopg.filter(~WorkOrder.pn.contains('NRU'), ~WorkOrder.pn.contains('FLYC'), ~WorkOrder.pn.contains('POC'),
                    ~WorkOrder.pn.contains('IGT'), ~WorkOrder.pn.contains('Nuvo'), ~WorkOrder.pn.contains('SEMIL')).count(),
    }
    product_mix28 = {k: v for k, v in product_mix28.items() if v > 0}

    # 28-day operator ranking
    completed_rank28 = uf(WorkOrder.query.filter((func.DATE(WorkOrder.intime)) >= (func.DATE(today - datetime.timedelta(days=28))), WorkOrder.status == 2))
    ranking28 = []
    for user in User.query.all():
        if user.role < 3:
            user_completed = completed_rank28.filter(WorkOrder.asid == user.id)
            cnt = user_completed.count()
            if cnt:
                score = CalculateScore(user_completed.order_by(WorkOrder.wo), basicscoreinfo)
                ranking28.append({'id': user.id, 'name': user.user_name, 'count': cnt, 'score': score})
    ranking28.sort(key=lambda r: r['score'], reverse=True)

    ranking_labels = [r['name'] for r in ranking]
    ranking_counts = [r['count'] for r in ranking]
    ranking_scores = [r['score'] for r in ranking]
    ranking_labels28 = [r['name'] for r in ranking28]
    ranking_counts28 = [r['count'] for r in ranking28]
    ranking_scores28 = [r['score'] for r in ranking28]

    # Quality Log data
    if use_custom_range:
        total_issues = QualityLog.query.filter(func.DATE(QualityLog.reporttime) >= func.DATE(sd),
                                                func.DATE(QualityLog.reporttime) <= func.DATE(ed)).count()
        open_issues = QualityLog.query.filter(QualityLog.status != 'Closed',
                                              func.DATE(QualityLog.reporttime) >= func.DATE(sd),
                                              func.DATE(QualityLog.reporttime) <= func.DATE(ed)).count()
        top_defects = db.session.query(QualityLog.defectpart, func.count(QualityLog.id).label('cnt')) \
            .filter(func.DATE(QualityLog.reporttime) >= func.DATE(sd),
                    func.DATE(QualityLog.reporttime) <= func.DATE(ed)) \
            .group_by(QualityLog.defectpart).order_by(func.count(QualityLog.id).desc()).limit(5).all()
        defect_causes = db.session.query(QualityLog.cause, func.count(QualityLog.id).label('cnt')) \
            .filter(QualityLog.cause != '', QualityLog.cause != None,
                    func.DATE(QualityLog.reporttime) >= func.DATE(sd),
                    func.DATE(QualityLog.reporttime) <= func.DATE(ed)) \
            .group_by(QualityLog.cause).order_by(func.count(QualityLog.id).desc()).limit(5).all()
    else:
        total_issues = QualityLog.query.count()
        open_issues = QualityLog.query.filter(QualityLog.status != 'Closed').count()
        top_defects = db.session.query(QualityLog.defectpart, func.count(QualityLog.id).label('cnt')) \
            .group_by(QualityLog.defectpart).order_by(func.count(QualityLog.id).desc()).limit(5).all()
        defect_causes = db.session.query(QualityLog.cause, func.count(QualityLog.id).label('cnt')) \
            .filter(QualityLog.cause != '', QualityLog.cause != None) \
            .group_by(QualityLog.cause).order_by(func.count(QualityLog.id).desc()).limit(5).all()
    quality_data = {
        'total': total_issues,
        'open': open_issues,
        'closed': total_issues - open_issues,
        'top_defects': [(d.defectpart, d.cnt) for d in top_defects],
        'defect_causes': [(c.cause, c.cnt) for c in defect_causes],
    }

    # When custom date range is active, 28-day data mirrors the filtered range
    if use_custom_range:
        trend28 = trend
        product_mix28 = product_mix
        ranking28 = ranking
        ranking_labels28 = ranking_labels
        ranking_counts28 = ranking_counts
        ranking_scores28 = ranking_scores

    # Detail table (per-operator build breakdown, same as report.html)
    def build_detail_table(base_q):
        rows = []
        users = [current_user] if role == 0 else User.query.all()
        for user in users:
            if role == 0 or user.role < 3:
                user_q = base_q.filter(WorkOrder.asid == user.id)
                if user_q.count():
                    row = [user.id, user.user_name]
                    nNRU = user_q.filter(WorkOrder.pn.contains("NRU"), WorkOrder.packgo != True).count() + user_q.filter(WorkOrder.pn.contains("FLYC"), WorkOrder.packgo != True).count()
                    row.append(nNRU)
                    nPoc = user_q.filter(WorkOrder.pn.contains("POC"), WorkOrder.packgo != True).count() + user_q.filter(WorkOrder.pn.contains("IGT"), WorkOrder.packgo != True).count()
                    row.append(nPoc)
                    nNuvo5 = user_q.filter(WorkOrder.pn.contains("Nuvo-5"), WorkOrder.packgo != True).count()
                    nNuvo6 = user_q.filter(WorkOrder.pn.contains("Nuvo-6"), WorkOrder.packgo != True).count()
                    nNuvo7 = user_q.filter(WorkOrder.pn.contains("Nuvo-7"), WorkOrder.packgo != True).count()
                    row.append(nNuvo5 + nNuvo6 + nNuvo7)
                    nOthers = user_q.filter(WorkOrder.pn.contains("GT"), WorkOrder.packgo != True).count() + user_q.filter(WorkOrder.pn.contains("SER-"), WorkOrder.packgo != True).count() + user_q.filter(WorkOrder.pn.contains("SER"), WorkOrder.packgo != True).count()
                    row.append(nOthers)
                    nNuvo8 = user_q.filter(WorkOrder.pn.contains("Nuvo-8"), WorkOrder.packgo != True).count()
                    row.append(nNuvo8)
                    nNuvo9 = user_q.filter(WorkOrder.pn.contains("Nuvo-9"), WorkOrder.packgo != True).count()
                    row.append(nNuvo9)
                    nNuvo10 = user_q.filter(WorkOrder.pn.contains("Nuvo-10"), WorkOrder.packgo != True).count()
                    row.append(nNuvo10)
                    nNuvo11 = user_q.filter(WorkOrder.pn.contains("Nuvo-11"), WorkOrder.packgo != True).count()
                    row.append(nNuvo11)
                    nSemil = user_q.filter(WorkOrder.pn.contains("SEMIL"), WorkOrder.packgo != True).count()
                    row.append(nSemil)
                    nTotal = nNRU + nPoc + nNuvo5 + nNuvo6 + nNuvo7 + nOthers + nNuvo8 + nNuvo9 + nNuvo10 + nNuvo11 + nSemil
                    row.append(nTotal)
                    nInsOS = user_q.filter(WorkOrder.osinstall != '').count()
                    row.append(nInsOS)
                    nInsGPU = user_q.filter(WorkOrder.gpuinstall == True).count()
                    row.append(nInsGPU)
                    nInsModule = user_q.count() - user_q.filter_by(gpuinstall=False, wifiinstall=False, caninstall=False, mezioinstall=False).count()
                    row.append(nInsModule)
                    nPackgo = user_q.filter(WorkOrder.packgo == True).count()
                    row.append(nPackgo)
                    nScore = CalculateScore(user_q.order_by(WorkOrder.wo), basicscoreinfo)
                    row.append(nScore)
                    rows.append(row)
        return rows

    if use_custom_range:
        detail_base = uf(WorkOrder.query.filter(func.DATE(WorkOrder.intime) >= func.DATE(sd),
                                                func.DATE(WorkOrder.intime) <= func.DATE(ed),
                                                WorkOrder.status == 2))
        detail_table = build_detail_table(detail_base)
        detail_table28 = detail_table
    else:
        detail_base7 = uf(WorkOrder.query.filter((func.DATE(WorkOrder.intime)) >= (func.DATE(today - datetime.timedelta(days=7))), WorkOrder.status == 2))
        detail_base28 = uf(WorkOrder.query.filter((func.DATE(WorkOrder.intime)) >= (func.DATE(today - datetime.timedelta(days=28))), WorkOrder.status == 2))
        detail_table = build_detail_table(detail_base7)
        detail_table28 = build_detail_table(detail_base28)

    return render_template('dashboard.html', cntToday=cntToday, cnt7day=cnt7day, cnt28day=cnt28day, cntCustom=cntCustom,
                           use_custom_range=use_custom_range, start_date=start_date, end_date=end_date,
                           backlog=backlog, ranking=ranking, ranking28=ranking28,
                            trend=trend, trend28=trend28, trend_days=trend_days,
                           trend_label=trend_label, trend_label28=trend_label28,
                           wo_data=wo_data, pg_data=pg_data, rma_data=rma_data, build_data=build_data,
                           wo_data28=wo_data28, pg_data28=pg_data28, rma_data28=rma_data28, build_data28=build_data28,
                            wo_total=wo_total, pg_total=pg_total, rma_total=rma_total,
                           wo_total28=wo_total28, pg_total28=pg_total28, rma_total28=rma_total28,
                           operator_trends=operator_trends, operator_trends28=operator_trends28,
                           operator_build=operator_build, operator_build28=operator_build28,
                           operator_wo=operator_wo, operator_wo28=operator_wo28,
                           operator_pg=operator_pg, operator_pg28=operator_pg28,
                           operator_rma=operator_rma, operator_rma28=operator_rma28,
                           product_mix=product_mix, product_mix28=product_mix28,
                           ranking_labels=ranking_labels, ranking_counts=ranking_counts,
                           ranking_scores=ranking_scores,
                           ranking_labels28=ranking_labels28, ranking_counts28=ranking_counts28,
                            ranking_scores28=ranking_scores28, quality_data=quality_data, userrole=role,
                            detail_table=detail_table, detail_table28=detail_table28,
                            rma_counts=rma_counts_val, rma_retail=rma_retail_val, rma_channel=rma_channel_val,                             rma_rate=rma_rate_data, doa_rate=doa_rate_data,
                            rma_months=rma_months, doa_months=doa_months, rma_eff_iw=rma_eff_iw, rma_eff_oow=rma_eff_oow)

@main.route('/api/workorder-counts')
@login_required
def api_workorder_counts():
    today = datetime.datetime.today()
    lw = today - datetime.timedelta(days=1)
    while lw.weekday() >= 5:
        lw -= datetime.timedelta(days=1)
    counts = {
        'unassigned': WorkOrder.query.filter_by(status=-1).count(),
        'pending': WorkOrder.query.filter_by(status=-2).count(),
        'bldtst': WorkOrder.query.filter_by(status=0).count(),
        'waiting_inspection': WorkOrder.query.filter_by(status=1).count(),
        'waiting_packing': WorkOrder.query.filter_by(status=3).count(),
        'packing': WorkOrder.query.filter_by(status=4).count(),
        'waiting_final': WorkOrder.query.filter_by(status=5).count(),
        'completed_today': WorkOrder.query.filter(func.DATE(WorkOrder.intime) == func.DATE(today), WorkOrder.status == 2).count(),
        'completed_lw': WorkOrder.query.filter(func.DATE(WorkOrder.intime) == func.DATE(lw), WorkOrder.status == 2).count(),
    }
    return counts

@main.route('/api/rma-customer-info')
@login_required
def api_rma_customer_info():
    customer = request.args.get('customer', '').strip()
    if not customer:
        return {'found': False}
    case = RmaCases.query.filter(RmaCases.customers.ilike(customer)).order_by(RmaCases.id.desc()).first()
    if not case:
        return {'found': False}
    return {
        'found': True,
        'contactname': case.rmacontactname,
        'email': case.rmacontactemail,
        'phone': case.rmacontactphone,
        'contactname1': case.rmacontactname1 or '',
        'email1': case.rmacontactemail1 or '',
        'phone1': case.rmacontactphone1 or '',
        'shippingaddress': case.shippingaddress or '',
    }

@main.route('/api/rma-pn-info')
@login_required
def api_rma_pn_info():
    pn = request.args.get('pn', '').strip()
    if not pn:
        return {'found': False}
    mapping = lookup_pn(pn)
    if not mapping:
        return {'found': False}
    return {
        'found': True,
        'unitsinabox': mapping.unitsinabox or '',
        'category': mapping.category or '',
        'notes': mapping.notes or '',
    }

@main.route('/')
@login_required
def display_workorders():
    role = get_userrole(current_user.id)
    if role == 0 :
        todoworkorder1 = WorkOrder.query.filter_by(status=-1,asid=-1)
        todoworkorder2 = WorkOrder.query.filter_by(status=-1,asid=current_user.id)
        todoworkorder  = todoworkorder1.union(todoworkorder2)
        pendingworkorder1 = WorkOrder.query.filter_by(status=-2,asid=-1)
        pendingworkorder2 = WorkOrder.query.filter_by(status=-2,asid=current_user.id)
        pendingworkorder  = pendingworkorder1.union(todoworkorder2)
    else :
        todoworkorder = WorkOrder.query.filter_by(status=-1)  
        pendingworkorder = WorkOrder.query.filter_by(status=-2)  
    todoworkorder = todoworkorder.order_by(WorkOrder.wo)    
    pendingworkorder = pendingworkorder.order_by(WorkOrder.wo)    
    def f(q):
        return q.filter if role == 0 else lambda **k: q.filter_by(**k) if len(k)==1 else q.filter(*[getattr(WorkOrder,k).__eq__(v) for k,v in k.items()])
    # Simpler approach: use role-based base
    def by_role(base):
        return base.filter(WorkOrder.asid == current_user.id) if role == 0 else base
    bldtst = by_role(WorkOrder.query.filter_by(status=0)).order_by(WorkOrder.wo)
    wfi = by_role(WorkOrder.query.filter_by(status=1)).order_by(WorkOrder.wo)  # wait inspection
    wfp = by_role(WorkOrder.query.filter_by(status=3)).order_by(WorkOrder.wo)  # wait for packing
    packing = by_role(WorkOrder.query.filter_by(status=4)).order_by(WorkOrder.wo)  # packing
    wffi = by_role(WorkOrder.query.filter_by(status=5)).order_by(WorkOrder.wo)  # wait for final inspect
    if role == 0 :
        completed = WorkOrder.query.filter(func.DATE(WorkOrder.intime) == func.DATE(datetime.datetime.today()),WorkOrder.asid==current_user.id,WorkOrder.status == 2)
    else :
        completed = WorkOrder.query.filter(func.DATE(WorkOrder.intime) == func.DATE(datetime.datetime.today()),WorkOrder.status == 2)
    completed = completed.order_by(WorkOrder.wo)
    today_dt = datetime.datetime.today()
    lw = today_dt - datetime.timedelta(days=1)
    while lw.weekday() >= 5:
        lw -= datetime.timedelta(days=1)
    if role == 0:
        completed_last_wd = WorkOrder.query.filter(func.DATE(WorkOrder.intime) == func.DATE(lw), WorkOrder.asid == current_user.id, WorkOrder.status == 2)
    else:
        completed_last_wd = WorkOrder.query.filter(func.DATE(WorkOrder.intime) == func.DATE(lw), WorkOrder.status == 2)
    completed_last_wd = completed_last_wd.order_by(WorkOrder.wo)
    unassigned_count = WorkOrder.query.filter_by(status=-1).count()
    pending_count = WorkOrder.query.filter_by(status=-2).count()
    bldtst_count = by_role(WorkOrder.query.filter_by(status=0)).count()
    wfi_count = by_role(WorkOrder.query.filter_by(status=1)).count()
    wfp_count = by_role(WorkOrder.query.filter_by(status=3)).count()
    packing_count = by_role(WorkOrder.query.filter_by(status=4)).count()
    wffi_count = by_role(WorkOrder.query.filter_by(status=5)).count()
    completed_today_count = WorkOrder.query.filter(func.DATE(WorkOrder.intime) == func.DATE(datetime.datetime.today()), WorkOrder.status == 2).count()
    lw = datetime.datetime.today() - datetime.timedelta(days=1)
    while lw.weekday() >= 5:
        lw -= datetime.timedelta(days=1)
    completed_lw_count = WorkOrder.query.filter(func.DATE(WorkOrder.intime) == func.DATE(lw), WorkOrder.status == 2).count()
    return render_template('home.html', todoworkorder=todoworkorder, pendingworkorder=pendingworkorder,
                           bldtst=bldtst, wfi=wfi, wfp=wfp, packing=packing, wffi=wffi,
                           completed=completed, completed_last_wd=completed_last_wd, userrole=role,
                           unassigned_count=unassigned_count, pending_count=pending_count,
                           bldtst_count=bldtst_count, wfi_count=wfi_count,
                           wfp_count=wfp_count, packing_count=packing_count, wffi_count=wffi_count,
                           completed_today_count=completed_today_count,
                           completed_lw_count=completed_lw_count)

@main.route('/query', methods=['GET', 'POST'])
@login_required
def query():
    form = QueryForm()
    if request.method == "POST":
        params = {}
        for f in ['startdate', 'enddate', 'wo', 'customers', 'pn', 'csn']:
            v = request.form.get(f, '')
            if v:
                params[f] = v
        op = request.form.get('operator', '')
        if op:
            params['operator'] = op
        if request.form.get('packgo'):
            params['packgo'] = '1'
        return redirect(url_for('main.query', **params))

    role = get_userrole(current_user.id)
    if role < 2:
        return redirect(url_for('main.display_workorders'))
    searched = 0
    completedss = WorkOrder.query.filter(WorkOrder.status == 2)
    if request.args.get('startdate') and request.args.get('enddate'):
        try:
            sd = datetime.datetime.strptime(request.args['startdate'], '%Y-%m-%d')
            ed = datetime.datetime.strptime(request.args['enddate'], '%Y-%m-%d')
            if ed >= sd:
                completedss = completedss.filter(func.DATE(WorkOrder.intime) >= func.DATE(sd),
                                                  func.DATE(WorkOrder.intime) <= func.DATE(ed))
                form.startdate.data = sd
                form.enddate.data = ed
        except: pass
    packgo = request.args.get('packgo')
    if packgo != '1':
        completedss = completedss.filter(WorkOrder.packgo != True)
    else:
        form.packgo.data = True
    op = request.args.get('operator', '')
    if op and op != '__None':
        try:
            asid = int(op)
            completedss = completedss.filter(WorkOrder.asid == asid)
            user = User.query.get(asid)
            if user:
                form.operator.data = user
        except: pass
    wo = request.args.get('wo', '')
    if wo:
        completedss = completedss.filter(WorkOrder.wo == wo)
        form.wo.data = wo
    pn = request.args.get('pn', '')
    if pn:
        completedss = completedss.filter(WorkOrder.pn.contains(pn))
        form.pn.data = pn
    csn = request.args.get('csn', '')
    if csn:
        completedss = completedss.filter(WorkOrder.csn.contains(csn))
        form.csn.data = csn
    customers = request.args.get('customers', '')
    if customers:
        completedss = completedss.filter(WorkOrder.customers.contains(customers))
        form.customers.data = customers
    if any(request.args.values()):
        completedss = completedss.order_by(WorkOrder.asid)
        searched = 1
    basicscoreinfo = PnMap.query.filter(PnMap.id!=0)
    searchtable = []
    tablesearchsummary = []
    if searched == 1:
        users = User.query.all()    
        for user in users :
            if user.role < 3 :
                if searched == 1:
                    completedssbyuser=completedss.filter(WorkOrder.asid == user.id)
                    if completedssbyuser.count() :
                    #calculate POC, Nuvo-5000, Nuvo-6000, Nuvo-7000, Nuvo-8000,Nuvo-9000, Muvo-10000, Pack&Go
                    #NRU, including FLYC-300
                        rows = []
                        rows.append(user.user_name)
                        nNRU = completedssbyuser.filter(WorkOrder.pn.contains("NRU")).filter(WorkOrder.packgo!=True).count() + completedssbyuser.filter(WorkOrder.pn.contains("FLYC")).filter(WorkOrder.packgo!=True).count()
                        rows.append(nNRU)
                        nPoc = completedssbyuser.filter(WorkOrder.pn.contains("POC")).filter(WorkOrder.packgo!=True).count()+completedssbyuser.filter(WorkOrder.pn.contains("IGT")).filter(WorkOrder.packgo!=True).count()
                        rows.append(nPoc)
                        nNuvo5= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-5")).filter(WorkOrder.packgo!=True).count()+completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-2")).filter(WorkOrder.packgo!=True).count()
                        nNuvo6= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-6")).filter(WorkOrder.packgo!=True).count()
                        nNuvo7= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-7")).filter(WorkOrder.packgo!=True).count()
                        rows.append(nNuvo5+nNuvo6+nNuvo7)
                        nOthers= completedssbyuser.filter(WorkOrder.pn.contains("GT")).filter(WorkOrder.packgo!=True).count()
                        nOthers= nOthers + completedssbyuser.filter(WorkOrder.pn.contains("SER-")).filter(WorkOrder.packgo!=True).count()
                        rows.append(nOthers)
                        nNuvo8= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-8")).filter(WorkOrder.packgo!=True).count()
                        rows.append(nNuvo8)
                        nNuvo9= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-9")).filter(WorkOrder.packgo!=True).count()
                        rows.append(nNuvo9)
                        nNuvoa= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-10")).filter(WorkOrder.packgo!=True).count()
                        rows.append(nNuvoa)
                        nNuvob= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-11")).filter(WorkOrder.packgo!=True).count()
                        rows.append(nNuvob)
                        nSemil= completedssbyuser.filter(WorkOrder.pn.contains("SEMIL")).filter(WorkOrder.packgo!=True).count()
                        rows.append(nSemil)
                        nTotal= nNRU + nPoc + nNuvo5 + nNuvo6 + nOthers + nNuvo7 + nNuvo8 + nNuvo9 + nNuvoa + nNuvob +nSemil
                        rows.append(nTotal)
                        nInsOS = completedssbyuser.filter(WorkOrder.osinstall != '').count()
                        rows.append(nInsOS)
                        nInsGPU = completedssbyuser.filter(WorkOrder.gpuinstall == True).count()
                        rows.append(nInsGPU)
                        nInsModule = completedssbyuser.count() - completedssbyuser.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False).count()
                        rows.append(nInsModule)
                        nPackgo= completedssbyuser.filter(WorkOrder.packgo==True).count()
                        rows.append(nPackgo)
                        nScore = CalculateScore(completedssbyuser.order_by(WorkOrder.wo),basicscoreinfo)
                        rows.append(nScore)
                        tablesearchsummary.append(rows)
        for workord in completedss :
            rows = []
            rows.append(workord.id)
            rows.append(workord.wo)
            rows.append(workord.customers)
            rows.append(workord.pn)
            rows.append(workord.csn)
            rows.append(workord.cstime.strftime("%m/%d %H:%M"))
            rows.append(workord.tktime.strftime("%m/%d %H:%M"))
            rows.append(get_username(workord.asid))
            rows.append(workord.astime.strftime("%m/%d %H:%M"))
            rows.append(get_username(workord.insid))
            rows.append(workord.intime.strftime("%m/%d %H:%M"))
            rows.append(CalculateUnitBuildScore(workord,basicscoreinfo))
            searchtable.append(rows)
    return render_template('query.html', form=form, userrole=role, searched=searched,tablesearchsummary=tablesearchsummary,searchtable=searchtable)

@main.route('/register/report', methods=['GET', 'POST'])
@login_required
def report():
    form = ReportSearchForm()
    searched = 0
    basicscoreinfo = PnMap.query.filter(PnMap.id!=0)
    if request.method == "POST":
        #Prepare the search results between start date and end date
        if form.enddate.data != None and form.startdate.data != None:
            if form.enddate.data >= form.startdate.data :
                completedss = WorkOrder.query.filter(func.DATE(WorkOrder.intime) >= func.DATE(form.startdate.data ),WorkOrder.status == 2)
                completedss = completedss.filter((func.DATE(WorkOrder.intime)) <= (func.DATE(form.enddate.data )))
                searched = 1
    role = get_userrole(current_user.id)
    if role < 2:
        return redirect(url_for('main.display_workorders'))

    completed = WorkOrder.query.filter(func.DATE(WorkOrder.intime) == func.DATE(datetime.datetime.today()),WorkOrder.status == 2)
    completed7day = WorkOrder.query.filter((func.DATE(WorkOrder.intime)) >= (func.DATE(datetime.datetime.today())-7),WorkOrder.status == 2)
    completed28day = WorkOrder.query.filter((func.DATE(WorkOrder.intime)) >= (func.DATE(datetime.datetime.today())-28),WorkOrder.status == 2)
    #Total
    cntToday = [0,0,0,0,0,0]
    cntToday[0] = completed.count()
    #Build, not Pack & Go
    cntToday[1] = cntToday[0] - completed.filter_by(packgo=True).count()
    #OS, installed OS
    cntToday[2] = cntToday[1] - completed.filter_by(osinstall='',packgo=False).count()
    #Module, installed module
    cntToday[3] = cntToday[1] - completed.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False, packgo=False).count()
    #Gpu, Installed GPU
    cntToday[4] = completed.filter_by(gpuinstall=True).count()
    #Score
    cntToday[5] = CalculateScore(completed.order_by(WorkOrder.wo),basicscoreinfo)

    #Total
    cnt7day = [0,0,0,0,0,0]
    cnt7day[0] = completed7day.count()
    #Build, not Pack & Go
    cnt7day[1] = cnt7day[0] - completed7day.filter_by(packgo=True).count()
    #OS, installed OS
    cnt7day[2] = cnt7day[1] - completed7day.filter_by(osinstall='',packgo=False).count()
    #Module, installed module
    cnt7day[3] = cnt7day[1] - completed7day.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False, packgo=False).count()
    #Gpu, Installed GPU
    cnt7day[4] = completed7day.filter_by(gpuinstall=True).count()
    #Score
    cnt7day[5] = CalculateScore(completed7day.order_by(WorkOrder.wo),basicscoreinfo)

    #Total
    cnt28day = [0,0,0,0,0,0]
    cnt28day[0] = completed28day.count()
    #Build, not Pack & Go
    cnt28day[1] = cnt28day[0] - completed28day.filter_by(packgo=True).count()
    #OS, installed OS
    cnt28day[2] = cnt28day[1] - completed28day.filter_by(osinstall='',packgo=False).count()
    #Module, installed module
    cnt28day[3] = cnt28day[1] - completed28day.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False, packgo=False).count()
    #Gpu, Installed GPU
    cnt28day[4] = completed28day.filter_by(gpuinstall=True).count()
    #Score
    cnt28day[5] = CalculateScore(completed28day.order_by(WorkOrder.wo),basicscoreinfo)

    #Last 2 wwek, 4 week performance
    # Operator name,  POC, Nuvo-5000, Nuvo-6000, Nuvo-7000, Nuvo-8000,Nuvo-9000, Muvo-10000, Pack&Go
    users = User.query.all()
    
    table1week  = []
    table2weeks = []
    table4weeks = []
    tablesearch = []
    for user in users :
        if user.role < 3 :
           completed1week  = WorkOrder.query.filter((func.DATE(WorkOrder.intime)) >= (func.DATE(datetime.datetime.today())-7),WorkOrder.status == 2, WorkOrder.asid == user.id)
           completed2weeks = WorkOrder.query.filter((func.DATE(WorkOrder.intime)) >= (func.DATE(datetime.datetime.today())-14),WorkOrder.status == 2, WorkOrder.asid == user.id)
           completed4weeks = WorkOrder.query.filter((func.DATE(WorkOrder.intime)) >= (func.DATE(datetime.datetime.today())-28),WorkOrder.status == 2, WorkOrder.asid == user.id)
           if searched == 1:
              completedssbyuser=completedss.filter(WorkOrder.asid == user.id)
              if completedssbyuser.count() :
              #calculate POC, Nuvo-5000, Nuvo-6000, Nuvo-7000, Nuvo-8000,Nuvo-9000, Muvo-10000, Pack&Go
                rows = []
                rows.append(user.user_name)
                nNRU = completedssbyuser.filter(WorkOrder.pn.contains("NRU")).filter(WorkOrder.packgo!=True).count() + completedssbyuser.filter(WorkOrder.pn.contains("FLYC")).filter(WorkOrder.packgo!=True).count()
                rows.append(nNRU)
                nPoc = completedssbyuser.filter(WorkOrder.pn.contains("POC")).filter(WorkOrder.packgo!=True).count()+completedssbyuser.filter(WorkOrder.pn.contains("IGT")).filter(WorkOrder.packgo!=True).count()
                rows.append(nPoc)
                nNuvo5= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-5")).filter(WorkOrder.packgo!=True).count()+completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-2")).filter(WorkOrder.packgo!=True).count()
                nNuvo6= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-6")).filter(WorkOrder.packgo!=True).count()
                nNuvo7= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-7")).filter(WorkOrder.packgo!=True).count()
                rows.append(nNuvo5+nNuvo6+nNuvo7)
                nOthers = completedssbyuser.filter(WorkOrder.pn.contains("GT")).filter(WorkOrder.packgo!=True).count()
                nOthers = nOthers + completedssbyuser.filter(WorkOrder.pn.contains("SER-")).filter(WorkOrder.packgo!=True).count()
                rows.append(nOthers)
                nNuvo8= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-8")).filter(WorkOrder.packgo!=True).count()
                rows.append(nNuvo8)
                nNuvo9= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-9")).filter(WorkOrder.packgo!=True).count()
                rows.append(nNuvo9)
                nNuvoa= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-10")).filter(WorkOrder.packgo!=True).count()
                rows.append(nNuvoa)
                nNuvob= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-11")).filter(WorkOrder.packgo!=True).count()
                rows.append(nNuvob)
                nSemil= completedssbyuser.filter(WorkOrder.pn.contains("SEMIL")).filter(WorkOrder.packgo!=True).count()
                rows.append(nSemil)
                nTotal= nNRU + nPoc + nNuvo5 + nNuvo6 + nNuvo7 + nOthers + nNuvo8 + nNuvo9 + nNuvoa + nNuvob + nSemil
                rows.append(nTotal)
                nInsOS = completedssbyuser.filter(WorkOrder.osinstall != '').count()
                rows.append(nInsOS)
                nInsGPU = completedssbyuser.filter(WorkOrder.gpuinstall == True).count()
                rows.append(nInsGPU)
                nInsModule = completedssbyuser.count() - completedssbyuser.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False).count()
                rows.append(nInsModule)
                nPackgo= completedssbyuser.filter(WorkOrder.packgo==True).count()
                rows.append(nPackgo)
                nScore = CalculateScore(completedssbyuser.order_by(WorkOrder.wo),basicscoreinfo)
                rows.append(nScore)
                tablesearch.append(rows)
           if completed1week.count() :
              #calculate POC, Nuvo-5000, Nuvo-6000, Nuvo-7000, Nuvo-8000,Nuvo-9000, Muvo-10000, Pack&Go
              rows = []
              rows.append(user.user_name)
              nNRU = completed1week.filter(WorkOrder.pn.contains("NRU")).filter(WorkOrder.packgo!=True).count() + completed1week.filter(WorkOrder.pn.contains("FLYC")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNRU)
              nPoc = completed1week.filter(WorkOrder.pn.contains("POC")).filter(WorkOrder.packgo!=True).count()+completed1week.filter(WorkOrder.pn.contains("IGT")).filter(WorkOrder.packgo!=True).count()
              rows.append(nPoc)
              nNuvo5= completed1week.filter(WorkOrder.pn.contains("Nuvo-5")).filter(WorkOrder.packgo!=True).count()+completed1week.filter(WorkOrder.pn.contains("Nuvo-2")).filter(WorkOrder.packgo!=True).count()
              nNuvo6= completed1week.filter(WorkOrder.pn.contains("Nuvo-6")).filter(WorkOrder.packgo!=True).count()
              nNuvo7= completed1week.filter(WorkOrder.pn.contains("Nuvo-7")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvo5+nNuvo6+nNuvo7)
              nOthers = completed1week.filter(WorkOrder.pn.contains("GT")).filter(WorkOrder.packgo!=True).count()  
              nOthers = nOthers + completed1week.filter(WorkOrder.pn.contains("GT")).filter(WorkOrder.packgo!=True).count()  
              rows.append(nOthers)
              nNuvo8= completed1week.filter(WorkOrder.pn.contains("Nuvo-8")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvo8)
              nNuvo9= completed1week.filter(WorkOrder.pn.contains("Nuvo-9")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvo9)
              nNuvoa= completed1week.filter(WorkOrder.pn.contains("Nuvo-10")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvoa)
              nNuvob =completed1week.filter(WorkOrder.pn.contains("Nuvo-11")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvob)
              nSemil= completed1week.filter(WorkOrder.pn.contains("SEMIL")).filter(WorkOrder.packgo!=True).count()
              rows.append(nSemil)
              nTotal= nNRU + nPoc + nNuvo5 + nNuvo6 + nNuvo7 + nOthers + nNuvo8 + nNuvo9 + nNuvoa + nNuvob + nSemil
              rows.append(nTotal)
              nInsOS = completed1week.filter(WorkOrder.osinstall != '').count()
              rows.append(nInsOS)
              nInsGPU = completed1week.filter(WorkOrder.gpuinstall == True).count()
              rows.append(nInsGPU)
              nInsModule = completed1week.count() - completed1week.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False).count()
              rows.append(nInsModule)
              nPackgo= completed1week.filter(WorkOrder.packgo==True).count()
              rows.append(nPackgo)
              nScore = CalculateScore(completed1week.order_by(WorkOrder.wo),basicscoreinfo)
              rows.append(nScore)
              table1week.append(rows)

           if completed2weeks.count() :
              #calculate POC, Nuvo-5000, Nuvo-6000, Nuvo-7000, Nuvo-8000,Nuvo-9000, Muvo-10000, Pack&Go
              rows = []
              rows.append(user.user_name)
              nNRU = completed2weeks.filter(WorkOrder.pn.contains("NRU")).filter(WorkOrder.packgo!=True).count() + completed2weeks.filter(WorkOrder.pn.contains("FLYC")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNRU)
              nPoc = completed2weeks.filter(WorkOrder.pn.contains("POC")).filter(WorkOrder.packgo!=True).count()+completed2weeks.filter(WorkOrder.pn.contains("IGT")).filter(WorkOrder.packgo!=True).count()
              rows.append(nPoc)
              nNuvo5= completed2weeks.filter(WorkOrder.pn.contains("Nuvo-5")).filter(WorkOrder.packgo!=True).count()+completed2weeks.filter(WorkOrder.pn.contains("Nuvo-2")).filter(WorkOrder.packgo!=True).count()
              nNuvo6= completed2weeks.filter(WorkOrder.pn.contains("Nuvo-6")).filter(WorkOrder.packgo!=True).count()
              nNuvo7= completed2weeks.filter(WorkOrder.pn.contains("Nuvo-7")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvo5+nNuvo6+nNuvo7)
              nOthers= completed2weeks.filter(WorkOrder.pn.contains("GT")).filter(WorkOrder.packgo!=True).count()
              nOthers= nOthers+completed2weeks.filter(WorkOrder.pn.contains("SER")).filter(WorkOrder.packgo!=True).count()
              rows.append(nOthers)
              nNuvo8= completed2weeks.filter(WorkOrder.pn.contains("Nuvo-8")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvo8)
              nNuvo9= completed2weeks.filter(WorkOrder.pn.contains("Nuvo-9")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvo9)
              nNuvoa= completed2weeks.filter(WorkOrder.pn.contains("Nuvo-10")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvoa)
              nNuvob= completed2weeks.filter(WorkOrder.pn.contains("Nuvo-11")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvob)
              nSemil= completed2weeks.filter(WorkOrder.pn.contains("SEMIL")).filter(WorkOrder.packgo!=True).count()
              rows.append(nSemil)
              nTotal= nNRU + nPoc + nNuvo5 + nNuvo6 + nNuvo7 + nOthers + nNuvo8 + nNuvo9 + nNuvoa + nNuvob + nSemil
              rows.append(nTotal)
              nInsOS = completed2weeks.filter(WorkOrder.osinstall != '').count()
              rows.append(nInsOS)
              nInsGPU = completed2weeks.filter(WorkOrder.gpuinstall == True).count()
              rows.append(nInsGPU)
              nInsModule = completed2weeks.count() - completed2weeks.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False).count()
              rows.append(nInsModule)
              nPackgo= completed2weeks.filter(WorkOrder.packgo==True).count()
              rows.append(nPackgo)
              nScore = CalculateScore(completed2weeks.order_by(WorkOrder.wo),basicscoreinfo)
              rows.append(nScore)
              table2weeks.append(rows)

           if completed4weeks.count() :
              #calculate POC, Nuvo-5000, Nuvo-6000, Nuvo-7000, Nuvo-8000,Nuvo-9000, Muvo-10000, Pack&Go
              rows = []
              rows.append(user.user_name)
              nNRU = completed4weeks.filter(WorkOrder.pn.contains("NRU")).filter(WorkOrder.packgo!=True).count() + completed4weeks.filter(WorkOrder.pn.contains("FLYC")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNRU)
              nPoc = completed4weeks.filter(WorkOrder.pn.contains("POC")).filter(WorkOrder.packgo!=True).count()+completed4weeks.filter(WorkOrder.pn.contains("IGT")).filter(WorkOrder.packgo!=True).count()
              rows.append(nPoc)
              nNuvo5= completed4weeks.filter(WorkOrder.pn.contains("Nuvo-5")).filter(WorkOrder.packgo!=True).count()+completed4weeks.filter(WorkOrder.pn.contains("Nuvo-2")).filter(WorkOrder.packgo!=True).count()
              nNuvo6= completed4weeks.filter(WorkOrder.pn.contains("Nuvo-6")).filter(WorkOrder.packgo!=True).count()
              nNuvo7= completed4weeks.filter(WorkOrder.pn.contains("Nuvo-7")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvo5+nNuvo6+nNuvo7)
              nOthers= completed4weeks.filter(WorkOrder.pn.contains("GT")).filter(WorkOrder.packgo!=True).count()
              nOthers= nOthers + completed4weeks.filter(WorkOrder.pn.contains("GT")).filter(WorkOrder.packgo!=True).count()
              rows.append(nOthers)
              nNuvo8= completed4weeks.filter(WorkOrder.pn.contains("Nuvo-8")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvo8)
              nNuvo9= completed4weeks.filter(WorkOrder.pn.contains("Nuvo-9")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvo9)
              nNuvoa= completed4weeks.filter(WorkOrder.pn.contains("Nuvo-10")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvoa)
              nNuvob= completed4weeks.filter(WorkOrder.pn.contains("Nuvo-11")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvob)
              nSemil= completed4weeks.filter(WorkOrder.pn.contains("SEMIL")).filter(WorkOrder.packgo!=True).count()
              rows.append(nSemil)
              nTotal= nNRU + nPoc + nNuvo5 + nNuvo6 + nNuvo7 + nOthers + nNuvo8 + nNuvo9 + nNuvoa + nNuvob + nSemil
              rows.append(nTotal)
              nInsOS = completed4weeks.filter(WorkOrder.osinstall != '').count()
              rows.append(nInsOS)
              nInsGPU = completed4weeks.filter(WorkOrder.gpuinstall == True).count()
              rows.append(nInsGPU)
              nInsModule = completed4weeks.count() - completed4weeks.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False).count()
              rows.append(nInsModule)
              nPackgo= completed4weeks.filter(WorkOrder.packgo==True).count()
              rows.append(nPackgo)
              nScore = CalculateScore(completed4weeks.order_by(WorkOrder.wo),basicscoreinfo)
              rows.append(nScore)
              table4weeks.append(rows)

    return render_template('report.html', cntToday=cntToday,cnt7day=cnt7day,cnt28day=cnt28day,userrole=role,table1week=table1week,table2weeks=table2weeks,table4weeks=table4weeks,form=form,tablesearch=tablesearch,searched=searched)
    
@main.route('/TakeOneComputer/<id>', methods=['GET', 'POST'])
@login_required
def TakeOneComputer(id): 
    workorder = WorkOrder.query.get(id)
    workorder.status=0
    workorder.asid=current_user.id
    workorder.tktime=datetime.datetime.now()
    db.session.commit()
    
    flash('TakeOneComputer successfully')
    return redirect(url_for('main.display_workorders'))

@main.route('/DeleteOneComputer/<id>', methods=['GET', 'POST'])
@login_required
def DeleteOneComputer(id): 
    workorder = WorkOrder.query.get(id)
    db.session.delete(workorder)
    products = Production.query.filter_by(wo = workorder.wo, csn =workorder.csn)
    if products.count() :
        db.session.delete(products[0])
    db.session.commit()
    flash('DeleteOneComputer successfully')
    return redirect(url_for('main.display_workorders'))

@main.route('/EditOneComputer/<id>', methods=['GET', 'POST'])
@login_required
def EditOneComputer(id): 
    workorder = WorkOrder.query.get(id)
    form = EditOneComputerForm(obj=workorder)
    #Explicitly load doc_items from database (in case obj population fails)
    if request.method == 'GET':
        form.doc_items.data = workorder.doc_items or ''
        print(f"Loading doc_items from DB: {workorder.doc_items}")
    role = get_userrole(current_user.id)
    if form.validate_on_submit():
        print(form.cpuinstall.data)
        workorder.wo=form.wo.data
        workorder.customers=form.customers.data
        workorder.pn=str(form.pn.data)
        workorder.csn=form.csn.data.strip()
        workorder.cputype = form.cputype.data
        workorder.memorysize = form.memorysize.data
        workorder.disksize = form.disksize.data
        workorder.cpuinstall = form.cpuinstall.data
        workorder.memoryinstall = form.memoryinstall.data
        workorder.gpuinstall = form.gpuinstall.data
        workorder.wifiinstall = form.wifiinstall.data
        workorder.mezioinstall = form.mezioinstall.data
        workorder.caninstall = form.caninstall.data
        workorder.fg5ginstall = form.fg5ginstall.data
        workorder.osinstall = form.osinstall.data
        workorder.packgo = form.packgo.data
        workorder.ldtime = form.ldtime.data
        workorder.gpu=form.gpu.data
        workorder.withwifi=form.withwifi.data
        workorder.withcan=form.withcan.data
        workorder.withfg5g=form.withfg5g.data
        workorder.ospreinstalled=form.ospreinstalled.data
        workorder.osactivation=form.osactivation.data
        workorder.diskpreinstalled=form.diskpreinstalled.data
        workorder.doc_items=form.doc_items.data
        if form.operator.data != None :
            asidset = form.operator.data.id
            workorder.asid = asidset    
        #Do not update    
        #workorder.csid = current_user.id
        #workorder.cstime=datetime.datetime.now()
        db.session.commit()
        flash('Update successful')
        #previous_url = form.previous_url.data 
        #redirect(url_for('main.queryworkorder'))
        #return redirect(url_for('main.display_workorders'))
    return render_template('edit_OneComputer.html', form=form, id=id, userrole=role) 

@main.route('/DeactiveOneComputer/<id>', methods=['GET', 'POST'])
@login_required
def DeactiveOneComputer(id): 
    workorder = WorkOrder.query.get(id)
    workorder.status=-2
    db.session.commit()
    
    flash('DeactiveOneComputer successfully')
    return redirect(url_for('main.display_workorders'))

@main.route('/RestoreOneComputer/<id>', methods=['GET', 'POST'])
@login_required
def RestoreOneComputer(id): 
    workorder = WorkOrder.query.get(id)
    workorder.status=-1
    db.session.commit()
    
    flash('RestoreOneComputer successfully')
    return redirect(url_for('main.display_workorders'))

@main.route('/UploadReport/<id>', methods=['GET', 'POST'])
@login_required
def UploadReport(id): 
    workorder = WorkOrder.query.get(id)
    workorder.astime=datetime.datetime.now()
    form = UploadReportForm(obj=workorder)
    role = get_userrole(current_user.id)
    if form.validate_on_submit():
        if workorder.status == 0:
            workorder.status = 3
            workorder.insid = current_user.id
        transaction = Production(wo=form.wo.data, pn=form.pn.data, csn=form.csn.data, msn=form.msn.data, cpu=form.cpu.data, 
            mem1=form.mem1.data, mem2=form.mem2.data, mem3=form.mem3.data, mem4=form.mem4.data, gpu1=form.gpu1.data, gpu2=form.gpu2.data, sata1=form.sata1.data, sata2=form.sata2.data,
            sata3=form.sata3.data, sata4=form.sata4.data, m21=form.m21.data, m22=form.m22.data, wifi=form.wifi.data, fg5g=form.fg5g.data,
            can=form.can.data,other=form.other.data,note=form.note.data,report=form.report.data)
        existproduct = Production.query.filter_by(wo=form.wo.data,csn=form.csn.data.strip())
        if existproduct.count() :
            db.session.delete(existproduct[0])
        db.session.add(transaction)
        db.session.commit()
        fstr = "Upload successful! "
        if workorder.cpuinstall == False and ("Nuvo" in workorder.pn or "SEMIL" in workorder.pn):
            fstr += "PLEASE uninstall CPU. "
        if workorder.memoryinstall == False and ("Nuvo" in workorder.pn or "POC" in workorder.pn or "SEMIL" in workorder.pn) :    
            fstr += "PLEASE uninstall Memory."
        if "WARNING" in form.note.data :
            fstr += form.note.data     
        flash(fstr)
        return redirect(url_for('main.display_workorders'))
    return render_template('uploadreport.html', form=form, id=id,userrole = role)

@main.route('/ReviewReport/<id>', methods=['GET', 'POST'])
@login_required
def ReviewReport(id):
        workorder = WorkOrder.query.get(id)
        products = Production.query.filter_by(wo=workorder.wo,csn=workorder.csn.strip())
        form = ReviewReportForm(obj=workorder)
        form.wo_doc_items.data = workorder.doc_items
        role = get_userrole(current_user.id)
        if products.count()>0 :
            product = products[0]
            if request.method == "GET":	
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
            if form.action.data == '0' :
                workorder.status = 2
                workorder.insid = current_user.id
            else: 
                workorder.status = 0  
            product.note=form.note.data # update notes
            product.cpu=form.cpu.data # update CPU
            product.m21=form.m21.data
            product.m22=form.m22.data
            db.session.commit()
            if(form.action.data=='0') :
               flash('Approved')
            else :
               flash('Denied')
            return redirect(url_for('main.display_workorders'))
        return render_template('reviewreport.html', form=form, id=id, userrole = role)

@main.route('/ViewReport/<wo>/<csn>', methods=['GET', 'POST'])
@login_required
def ViewReport(wo,csn):
        products = Production.query.filter_by(wo=wo,csn=csn)
        workorder = WorkOrder.query.filter_by(wo=wo,csn=csn)
        form = ViewReportForm(obj=products[0])
        form.wo_doc_items.data=workorder[0].doc_items
        role = get_userrole(current_user.id)
        return render_template('viewreport.html', form=form, userrole = role)


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

CPU_PN_MAP = {
    'GC-J-AGX64GB-Orin-Nvidia-601': 'AGX Orin 64GB',
    'GC-Jetson-AGX-Xavier-Nvidia': 'AGX Xavier 32GB',
    'GC-Jetson-AGX32GB-Orin-Nvidia': 'AGX Orin 32GB',
    'GC-Jetson-AGX64GB-Orin-Nvidia': 'AGX Orin 64GB',
    'GC-Jetson-AGXi-Xavier-NVIDIA': 'AGX Xavier 32GB Industrial',
    'GC-Jetson-NO8G-Orin-Nvidia': 'Orin Nano 8GB',
    'GC-Jetson-NX-Xavier-Nvidia': 'Xavier NX 8GB',
    'GC-Jetson-NX16G-Orin-Nvidia': 'Orin NX 16GB',
    'GC-Jetson-NX16GB-Xavier-Nvidia': 'Xavier NX 16GB',
    'GC-Jetson-NX8G-Orin-Nvidia': 'Orin NX 8GB',
    'GC-Jetson-T5128GB-Thor-Nvidia': 'Thor 512GB',
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSION 

def get_header_tables(doc):
    header_tables = []
    for section in doc.sections:
        header = section.header
        for element in header._element.xpath('//w:tbl'):
            table = docx.table.Table(element, header)
            header_tables.append(table)
    return header_tables

@main.route('/register/workorder', methods=['GET', 'POST'])
@login_required
def add_workorder():
    form = AddWorkorderForm()
    role = get_userrole(current_user.id)
    if request.method == 'POST' :
        print(f"DEBUG: form.doc_items = {form.doc_items.data}")
        #Restore doc_items from session if not in form data
        if not form.doc_items.data and 'doc_items' in session:
            form.doc_items.data = session['doc_items']
            print(f"Restored doc_items from session: {form.doc_items.data}")
        if 'readdocfile' in request.form :
           if request.form['readdocfile'] == 'Upload' and 'file' in  request.files:
                file = request.files['file'] 
                print(file.filename)
                if file.filename == '' :
                   return 'No selected file'
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(UPLOAD_FOLDER,filename)
                    file.save(filepath)
                    #Extract text fome the .docx file
                    doc = Document(filepath)
                    wocontent = []
                    linecnt = 0
                    colcnt = 0
                    foundPN = False
                    foundWO = False  
                    searchend = False 
                    customer = []
                    #Get customer information
                    header_tables = get_header_tables(doc)
                    for table in header_tables :
                            if not searchend :
                                for row in table.rows :
                                    colcnt = 0
                                    linecontent = []
                                    if not searchend :
                                        for cell in row.cells:
                                            if not foundWO :
                                                if colcnt == 0 and 'Customer' in cell.text:
                                                #find 
                                                    foundWO = True
                                                    linecontent.append(cell.text)
                                            else :       
                                                linecontent.append(cell.text)
                                            colcnt = colcnt + 1   
                                        customer.append(linecontent)
                                searchend =  foundWO
                    for row in customer :
                        if 'NTA Order ID' in row:
                            form.wo.data = row[1]
                        else :
                            for cell in row :
                                if 'Customer' == cell.strip():    
                                    form.customers.data = row[1]
                    searchend = False                                          
                    #Search content
                    doc_items_list = []  # Collect items for doc_items field
                    for table in doc.tables :
                            if not searchend :
                                for row in table.rows :
                                    colcnt = 0
                                    linecontent = []
                                    if not searchend :
                                        for cell in row.cells:
                                            if not foundPN :
                                                if colcnt == 0 and 'Product Number' in cell.text:
                                                    #find 
                                                    foundPN = True
                                                    linecontent.append(cell.text)
                                            else :       
                                                linecontent.append(cell.text)
                                            if 'End of Part' in cell.text :
                                                searchend = True
                                                break; 
                                            colcnt = colcnt + 1   
                                        wocontent.append(linecontent)
                                        #Collect item name for doc_items (column 0 = Product Number)
                                        if len(linecontent) > 0 and linecontent[0].strip() and 'Product Number' not in linecontent[0]:
                                            item_name = linecontent[0].strip()
                                            #Add quantity if available (column 1 = QTY)
                                            if len(linecontent) > 1 and linecontent[1].strip().isdigit():
                                                item_name = item_name + 'x' + linecontent[1].strip()
                                            doc_items_list.append(item_name)
                                #print(wocontent)
                    #Set doc_items field with items separated by |
                    doc_items_str = '|'.join(doc_items_list)
                    form.doc_items.data = doc_items_str
                    session['doc_items'] = doc_items_str  # Persist in session
                    print(f"Saved doc_items to session: {doc_items_str}")
                    #['Product Number', 'QTY', 'S/N', 'Notes', 'Check']
                    form.pn.data = wocontent[1][0]
                    count = int(wocontent[1][1])
                    form.csn.data = wocontent[1][2]
                    form.disksize.data=''
                    for row in wocontent :
                        if  'DDR3' in row[0] or 'DDR4' in row[0] or 'DDR5' in row[0]:
                            ddrcnt = int(row[1]) / count
                            ddrstr = row[0].split('-')
                            for ddrsize in ddrstr :
                                if 'GB' in ddrsize :
                                    form.memorysize.data = ddrsize + 'x' + str(int(ddrcnt))
                            if 'installed' not in row[3] :
                                form.memoryinstall.data = True
                            else :
                                form.memoryinstall.data = False
                        elif 'SSD' in row[0].upper() or 'HDD' in row[0].upper():
                            ssdcnt = int(row[1]) / count
                            ssdstr = row[0].split('-')
                            for ssdsize in ssdstr :
                                if 'GB' in ssdsize.upper() or 'TB' in ssdsize.upper():
                                    if 'PCIE' in row[0].upper() or 'P34' in row[0].upper() or 'P44' in row[0].upper():
                                        form.disksize.data = form.disksize.data + 'NVME' + ssdsize + 'x' + str(int(ssdcnt)) + '  '
                                    else :
                                        form.disksize.data = form.disksize.data + 'SSD' + ssdsize + 'x' + str(int(ssdcnt)) + '  '    
                            if 'installed' not in row[3] :
                                form.diskpreinstalled.data = False
                            else :
                                form.diskpreinstalled.data = True
                        elif 'RTX' in row[0].upper() or 'GTX' in row[0].upper() :
                            gpucnt = int(row[1]) / count
                            #gpustr = row[0].split('-')
                            #for gpusize in gpustr :
                            #    if 'RTX' in gpusize or 'GTX' in gpusize :
                            #        form.gpu.data = gpusize + 'x' + str(int(gpucnt))
                            #keep original GPU card information
                            form.gpu.data = row[0].strip()+ 'x' + str(int(gpucnt))
                            if 'installed' not in row[3] :
                                form.gpuinstall.data = True
                            else :
                                form.gpuinstall.data = False
                        elif  'CAN' in row[0].upper():
                            form.withcan.data = True
                            if 'installed' not in row[3] :
                                form.caninstall.data = True
                        elif 'WIFI' in row[0].upper():
                            form.withwifi.data = True
                            if 'installed' not in row[3] :
                                form.wifiinstall.data = True
                        elif 'MEZIO' in row[0].upper():   
                            if 'installed' not in row[3] :
                                form.mezioinstall.data = True
                        elif  'LTE-7455' in row[0] :   
                            form.withfg5g.data = True
                            if 'installed' not in row[3] :
                                form.fg5ginstall.data = True
                        elif 'WIN' in row[0].upper() or 'UBUNTU' in row[0].upper() or 'JP' in row[0].upper() \
                                or 'JETSON' in row[0].upper():
                            form.osinstall.data = row[0]
                            if 'installed' not in row[3] :
                                form.osinstall.data = row[0]
                            else :
                                form.ospreinstalled.data = True   
                        elif 'I7-' in row[0].upper() or 'I9-' in row[0].upper() or 'E22' in row[0].upper() \
                             or 'I3-' in row[0].upper() or 'I5-' in row[0].upper()  \
                             or 'AGX' in row[0].upper() or 'ORIN' in row[0].upper() :
                            form.cputype.data = CPU_PN_MAP.get(row[0].strip(), row[0])
                            if 'installed' not in row[3] :
                                form.cpuinstall.data = True
                            else :
                                form.cpuinstall.data = False
                    os.remove(filepath)
        elif form.validate_on_submit():
            print(f"DEBUG: doc_items before save: {form.doc_items.data}")
            if form.operator.data == None :
                asidset =-1
            else :
                asidset = form.operator.data.id   
            csn_m=form.csn.data.split('\n')
            for x in csn_m:
                if x.strip() != '' :
                    transaction = WorkOrder(wo=form.wo.data.replace("/","-"), customers=form.customers.data, pn=str(form.pn.data), csn=x.strip(), 
                    cputype=form.cputype.data,memorysize=form.memorysize.data,disksize=form.disksize.data,cpuinstall=form.cpuinstall.data,memoryinstall=form.memoryinstall.data,gpuinstall=form.gpuinstall.data,
                    wifiinstall=form.wifiinstall.data,mezioinstall=form.mezioinstall.data,caninstall=form.caninstall.data,fg5ginstall=form.fg5ginstall.data,
                    gpu=form.gpu.data,withwifi=form.withwifi.data,withcan=form.withcan.data,withfg5g=form.withfg5g.data,ospreinstalled=form.ospreinstalled.data,
                    osactivation=form.osactivation.data,diskpreinstalled=form.diskpreinstalled.data,
                    osinstall=form.osinstall.data,packgo=form.packgo.data,asid=asidset,insid=-1,astime=None,intime=None,tktime=None,csid=current_user.id,cstime=datetime.datetime.now(),ldtime=form.ldtime.data,status=-1,
                    doc_items=form.doc_items.data)
                    db.session.add(transaction)
            #Clear session after save
            if 'doc_items' in session:
                session.pop('doc_items')
            db.session.commit()
            flash('WorkOrder registered successfully')
            return redirect(url_for('main.display_workorders'))
    productlist = PnMap.query.with_entities(PnMap.pn).all()
    products = []
    for x in productlist :
        pns = f"{x}"
        pns = pns.replace("('","")
        pns = pns.replace("',)","")
        products.append(pns)
    return render_template('add_workorder.html', form=form, userrole = role,products=products)

@main.route('/CheckWorkOrder/<id>', methods=['GET', 'POST'])
@login_required
def CheckWorkOrder(id): 
    workorder = WorkOrder.query.get(id)
    form = ReviewOneComputerForm(obj=workorder)
    biosver = get_biosversion(workorder.pn)
    sopver  = get_sopversion(workorder.pn)
    form.biosver.data = biosver
    form.sopver.data = sopver
    role = get_userrole(current_user.id)
    if form.validate_on_submit():
        return redirect(url_for('main.display_workorders'))
    return render_template('CheckWorkOrder.html', form=form, id=id, userrole = role, biosver=biosver) 
def getcustomizedstr(item):
    customizedstr ="" 
    if item & 1 :
       customizedstr = customizedstr + " BIOS"
    if item & 2 :
       customizedstr = customizedstr + " SOP"     
    if item & 4 :
       customizedstr = customizedstr + " Chassis"   
    return customizedstr
@main.route('/customized', methods=['GET', 'POST'])
@login_required
def customized(): 
    customizedmodels = PnMap.query.filter(PnMap.customized!=0)
    role = get_userrole(current_user.id)
    return render_template('Customized.html', customizedmodels=customizedmodels, userrole = role,getcustomizedstr=getcustomizedstr) 

@main.route('/queryproduct', methods=['GET', 'POST'])
@login_required
def queryproduct():
    form = QueryProductsForm()
    if request.method == "POST":
        return redirect(url_for('main.queryproduct', pn=request.form.get('pn', '')))
    role = get_userrole(current_user.id)
    if role < 2:
        return redirect(url_for('main.display_workorders'))
    products = PnMap.query.filter(PnMap.id!=0)
    pn = request.args.get('pn', '')
    if pn:
        products = products.filter(PnMap.pn.contains(pn))
        form.pn.data = pn
    return render_template('query_products.html', form=form, userrole=role, searched=1 if pn else 0, products=products)

@main.route('/rmaparts', methods=['GET', 'POST'])
@login_required
def rmaparts():
    role = get_userrole(current_user.id)
    if role < 2:
        return redirect(url_for('main.display_workorders'))
    msg = ''
    if request.method == 'POST':
        partsname = request.form.get('partsname', '').strip()
        category = request.form.get('category', '').strip()
        workwith = request.form.get('workwith', '').strip()
        if not partsname:
            msg = 'Parts Name is required'
        elif RmaParts.query.filter_by(partsname=partsname).count():
            msg = f'Parts "{partsname}" already exists'
        else:
            db.session.add(RmaParts(partsname=partsname, category=category, workwith=workwith))
            db.session.commit()
            msg = f'Parts "{partsname}" created'
    all_parts = RmaParts.query.order_by(RmaParts.category, RmaParts.partsname).all()
    rma_names = {p.partsname for p in all_parts}
    available = [{
        'partsname': p.partsname,
        'partsn': p.partsn,
        'warehouse': p.warehouse or '',
        'history': p.history or '',
    } for p in PartsInventory.query.filter(PartsInventory.partsname.in_(rma_names), PartsInventory.warehouse.in_(('WH10', 'WH12', 'WH04'))).order_by(PartsInventory.partsname, PartsInventory.partsn).all()]
    return render_template('rmaparts.html', parts=all_parts, available=available,
                           warehouses=['WH10', 'WH04', 'WH12'], msg=msg, userrole=role,
                           productlist=[p[0] for p in PnMap.query.with_entities(PnMap.pn).all()])

@main.route('/rmaparts/sns', methods=['GET'])
@login_required
def rmaparts_sns():
    if get_userrole(current_user.id) < 2: abort(403)
    warehouse = request.args.get('warehouse', '').strip().upper()
    partsname = request.args.get('partsname', '').strip()
    if warehouse not in ('WH10', 'WH12'):
        return {'sns': []}
    sns = [p.partsn for p in PartsInventory.query.filter_by(warehouse=warehouse, partsname=partsname).all()]
    return {'sns': sns}

@main.route('/rmaparts/transfer', methods=['POST'])
@login_required
def rmaparts_transfer():
    if get_userrole(current_user.id) < 2: abort(403)
    partsname = request.form.get('partsname', '').strip()
    partsn = request.form.get('partsn', '').strip()
    target = request.form.get('target', '').strip().upper()
    if target not in ('WH10', 'WH04', 'WH12'):
        flash('Invalid target warehouse')
        return redirect(url_for('main.rmaparts'))
    rows = PartsInventory.query.filter_by(partsname=partsname, partsn=partsn).all()
    if not rows:
        flash(f'No inventory found for "{partsname}" / "{partsn}"')
        return redirect(url_for('main.rmaparts'))
    now = datetime.datetime.now().strftime('%m/%d/%Y %H:%M')
    for r in rows:
        old = r.warehouse or ''
        r.warehouse = target
        entry = f"[{now}] Transferred {old} -> {target}"
        r.history = (r.history.rstrip() + '\n' + entry) if r.history else entry
    db.session.commit()
    flash(f'Transferred {len(rows)} item(s) of "{partsname}" / "{partsn}" to {target}')
    return redirect(url_for('main.rmaparts'))

@main.route('/rmaparts/edit', methods=['POST'])
@login_required
def rmaparts_edit():
    if get_userrole(current_user.id) < 2: abort(403)
    partsname = request.form.get('partsname', '').strip()
    category = request.form.get('category', '').strip()
    workwith = request.form.get('workwith', '').strip()
    part = RmaParts.query.filter_by(partsname=partsname).first()
    if not part:
        flash(f'Parts "{partsname}" not found')
        return redirect(url_for('main.rmaparts'))
    part.category = category
    part.workwith = workwith
    db.session.commit()
    flash(f'Parts "{partsname}" updated')
    return redirect(url_for('main.rmaparts'))

@main.route('/rmaparts/receive', methods=['POST'])
@login_required
def rmaparts_receive():
    if get_userrole(current_user.id) < 2: abort(403)
    partsname = request.form.get('partsname', '').strip()
    warehouse = request.form.get('warehouse', '').strip().upper()
    sns = [x.strip() for x in request.form.get('partsn', '').replace(',', ' ').split() if x.strip()]
    if not partsname or not sns or warehouse not in ('WH10', 'WH12'):
        flash('Parts Name, Serial Number(s), and Warehouse are required', 'danger')
        return redirect(url_for('main.rmaparts'))
    if not RmaParts.query.filter_by(partsname=partsname).count():
        flash(f'Parts "{partsname}" does not exist in rmaparts', 'danger')
        return redirect(url_for('main.rmaparts'))
    inv_time = datetime.datetime.now().strftime('%m/%d/%Y %H:%M')
    cnt = 0
    skipped = 0
    for sn in sns:
        if PartsInventory.query.filter_by(partsname=partsname, partsn=sn).count():
            skipped += 1
            continue
        db.session.add(PartsInventory(partsname=partsname, partsn=sn, warehouse=warehouse, history=f"[{inv_time}] Received"))
        cnt += 1
    db.session.commit()
    msg = f'Received {cnt} item(s) of "{partsname}" into {warehouse}'
    if skipped:
        msg += f' ({skipped} duplicate SN(s) skipped)'
    flash(msg)
    return redirect(url_for('main.rmaparts'))

@main.route('/rmaparts/addlog', methods=['POST'])
@login_required
def rmaparts_addlog():
    if get_userrole(current_user.id) < 2: abort(403)
    partsname = request.form.get('partsname', '').strip()
    partsn = request.form.get('partsn', '').strip()
    logtext = request.form.get('logtext', '').strip()
    if not logtext:
        flash('Log content is required')
        return redirect(url_for('main.rmaparts'))
    rows = PartsInventory.query.filter_by(partsname=partsname, partsn=partsn).all()
    if not rows:
        flash(f'No inventory found for "{partsname}" / "{partsn}"')
        return redirect(url_for('main.rmaparts'))
    now = datetime.datetime.now().strftime('%m/%d/%Y %H:%M')
    entry = f"[{now}] {logtext}"
    for r in rows:
        r.history = (r.history.rstrip() + '\n' + entry) if r.history else entry
    db.session.commit()
    flash(f'Log added to "{partsname}" / "{partsn}"')
    return redirect(url_for('main.rmaparts'))


@main.route('/createproduct', methods=['GET', 'POST'])
@login_required
def createproduct():
    form = AddProductForm()
    role = get_userrole(current_user.id)
    if form.validate_on_submit():
        customizedvalue = 0
        if(form.customizedBIOS.data==True) :
            customizedvalue = customizedvalue + 1
        if(form.customizedSOP.data==True) :
            customizedvalue = customizedvalue + 2
        if(form.customizedOSImage.data==True) :
            customizedvalue = customizedvalue + 4
        if(form.customizedMechincal.data==True) :
            customizedvalue = customizedvalue + 8    
        if(form.customizedPackage.data==True) :
            customizedvalue = customizedvalue + 16    
        if(form.customizedLabel.data==True) :
            customizedvalue = customizedvalue + 32    
        transaction = PnMap(pn = form.pn.data.strip(), biosv = form.biosv.data, prefix = form.prefix.data, 
                            net = form.net.data, poe = form.poe.data, ign = form.ign.data, 
                            sop = form.sop.data, unitsinabox = form.unitsinabox.data, 
                            buildpoints = form.buildpoints.data, customized=customizedvalue, 
                            testonlypoints=form.testonlypoints.data,gpu=form.gpu.data,extra=form.extra.data,
                            abbreviation=form.abbreviation.data,category=form.category.data,
                            height=form.height.data,width=form.width.data,thickness=form.thickness.data,weight=form.weight.data,
                            inneraccessory=form.inneraccessory.data,notes=form.notes.data)
        db.session.add(transaction)
        db.session.commit()
        flash('Create Product Successfully')
        return redirect(url_for('main.createproduct'))
    return render_template('create_OneProduct.html', form=form, id=id, userrole=role) 

@main.route('/EditProduct/<id>', methods=['GET', 'POST'])
@login_required
def EditProduct(id): 
    id = int(id) # convert string to integer
    product = PnMap.query.get(id)
    form = EditProductForm(obj=product)
    role = get_userrole(current_user.id)
    #if request.method == 'GET' :
    #    session['previous_url'] = request.url
    if form.validate_on_submit():
        # Not update product name
        #product.pn = form.pn.data
        product.biosv = form.biosv.data
        product.prefix = form.prefix.data
        product.net = form.net.data
        product.poe = form.poe.data
        product.ign = form.ign.data
        product.sop = form.sop.data
        product.unitsinabox = form.unitsinabox.data
        product.buildpoints = form.buildpoints.data
        product.customized = form.customized.data
        product.testonlypoints = form.testonlypoints.data
        product.gpu = form.gpu.data
        product.extra = form.extra.data
        product.abbreviation = form.abbreviation.data
        product.category = form.category.data
        product.height = form.height.data
        product.width = form.width.data
        product.thickness = form.thickness.data
        product.weight = form.weight.data
        product.inneraccessory = form.inneraccessory.data
        product.notes = form.notes.data
        db.session.commit()
        flash('Update successful')
        #return redirect(session.get('previous_url','/'))
        #return redirect(url_for('main.queryproduct'))
    return render_template('edit_Product.html', form=form, id=id, userrole=role) 

@main.route('/queryworkorder', methods=['GET', 'POST'])
@login_required
def queryworkorder():
    form = QueryWorkordersForm()
    if request.method == "POST":
        return redirect(url_for('main.queryworkorder', wo=request.form.get('wo', '')))
    role = get_userrole(current_user.id)
    if role < 2:
        return redirect(url_for('main.queryworkorder'))
    workorders = WorkOrder.query.filter(WorkOrder.id!=0)
    wo = request.args.get('wo', '')
    if wo:
        workorders = workorders.filter(WorkOrder.wo.contains(wo))
        form.wo.data = wo
    return render_template('query_workorders.html', form=form, userrole=role, searched=1 if wo else 0, workorders=workorders)


@main.route('/packingcalculator', methods=['GET', 'POST'])
def packingcalculator():
    searched = 0
    solutions = []
    details = []
    totalpercentage = 0
    packing_data = []
    userrole = 0

    form = PackingCalculateForm()
    if request.method == "POST":
        searched = 1
    if form.validate_on_submit():    
        #Calculate packing solution
        # Get boxes from database
        boxes = PackageBox.query.filter_by(status=1).all() #general use, avaliable
        Boxes = []
        Boxes_SEMIL = []
        Boxes_RGS = []
        for box in boxes:
            Boxes.append(Box('Platform1', box.name, box.width, box.thickness, box.height, box.limitweight - box.weight, box.weight))
       
        platforms = {'Platform1':Boxes}
        #get payload from form input
        packages= []
        card1_qty = 0
        card2_qty = 0
        gpu_qty = 0
        poweradaptor_qty = 0
        cablekit1_qty = 0
        cablekit2_qty = 0
        dinrail_qty = 0
        dmpbr_qty = 0
        fankit_qty = 0
        wallmount_qty = 0
        camera_qty = 0
        computer_qty = 0
        if len(form.computer.data.strip()) :
           computer_name = form.computer.data
           computer_qty = form.qty_computer.data
        inneraccessory_name = ''
        dinrail_name = ''; dinrail_qty = 0
        dmpbr_name = ''; dmpbr_qty = 0
        fankit_name = ''; fankit_qty = 0
        wallmount_name = ''; wallmount_qty = 0
        card1_name = ''; card1_qty = 0
        card2_name = ''; card2_qty = 0
        gpu_name = ''; gpu_qty = 0
        poweradaptor_name = ''; poweradaptor_qty = 0
        cablekit1_name = ''; cablekit1_qty = 0
        cablekit2_name = ''; cablekit2_qty = 0
        camera_name = ''; camera_qty = 0
        if computer_qty != 0: #preinstalled computer
            computer = PnMap.query.filter_by(pn=computer_name).first()
            computer_weight = computer.weight
            if 'SEMIL' in computer.abbreviation :
                boxes = PackageBox.query.filter(PackageBox.purpose.like('%SEMIL%')).all() 
                for box in boxes:
                    Boxes_SEMIL.append(Box('Platform1', box.name, box.width, box.thickness, box.height, box.limitweight - box.weight, box.weight))
            if 'RGS' in computer.abbreviation :
                boxes = PackageBox.query.filter(PackageBox.purpose.like('%RGS%')).all() 
                for box in boxes:
                    Boxes_RGS.append(Box('Platform1', box.name, box.width, box.thickness, box.height, box.limitweight - box.weight, box.weight))

            if form.dinrail.data != None and form.qty_dinrail.data!=0: 
                dinrail_name = form.dinrail.data.pn
                dinrail_qty  = form.qty_dinrail.data
                if 'DINRAIL' in computer.inneraccessory:
                   inneraccessory_name = inneraccessory_name + '|DINRL'
                   computer_weight += PnMap.query.filter_by(pn=dinrail_name).first().weight # Add 0.5lbs for DIN RAIL
                   dinrail_qty = dinrail_qty - computer_qty
            if form.dmpbr.data != None and form.qty_dmpbr.data!=0: 
                dmpbr_name = form.dmpbr.data.pn
                dmpbr_qty  = form.qty_dmpbr.data
                inneraccessory_name = inneraccessory_name + '|DMPBR'
                computer_weight +=  PnMap.query.filter_by(pn=dmpbr_name).first().weight # Add 2lbs for Dumping Bracket
                dmpbr_qty = dmpbr_qty - computer_qty
            if form.fankit.data != None and form.qty_fankit.data!=0: 
                fankit_name = form.fankit.data.pn
                fankit_qty  = form.qty_fankit.data
                inneraccessory_name = inneraccessory_name + '|FKIT'
                computer_weight +=  PnMap.query.filter_by(pn=fankit_name).first().weight# Add 0.6lbs for FAN kit
                fankit_qty = fankit_qty - computer_qty
            if form.wallmount.data != None and form.qty_wallmount.data !=0: 
                wallmount_name = form.wallmount.data.pn
                wallmount_qty  = form.qty_wallmount.data
                inneraccessory_name = inneraccessory_name + '|WMNT'
                computer_weight += PnMap.query.filter_by(pn=wallmount_name).first().weight # Add 0.3lbs for Wall Mount
                wallmount_qty = wallmount_qty - computer_qty
            if form.card1.data != None and form.qty_card1.data!=0: 
                card1_name = form.card1.data.pn
                card1_qty  = form.qty_card1.data
                inneraccessory_name = inneraccessory_name + '|' + form.card1.data.pn 
                computer_weight +=  PnMap.query.filter_by(pn=card1_name).first().weight # Add 0.5lbs for PCIe card
                card1_qty = card1_qty - computer_qty
            if form.card2.data != None and form.qty_card2.data!=0: 
                card2_name = form.card2.data.pn
                card2_qty  = form.qty_card2.data
                inneraccessory_name = inneraccessory_name + '|' + form.card2.data.pn 
                computer_weight +=  PnMap.query.filter_by(pn=card2_name).first().weight # Add 0.5lbs for PCIe card
                card2_qty = card2_qty - computer_qty
            if form.gpu.data != None and form.qty_gpu != 0: 
                gpu_name = form.gpu.data.pn
                gpu_qty  = form.qty_gpu.data
                inneraccessory_name = inneraccessory_name + '|' + form.gpu.data.pn
                computer_weight +=  PnMap.query.filter_by(pn=gpu_name).first().weight*(gpu_qty/computer_qty) # Add 0.5lbs for PCIe card
                gpu_qty = gpu_qty - (gpu_qty/computer_qty)*computer_qty
            if form.poweradaptor.data != None and form.qty_poweradaptor.data !=0 :
                poweradaptor_name = form.poweradaptor.data.pn
                poweradaptor_qty  = form.qty_poweradaptor.data
                abbreviation_name = PnMap.query.filter_by(pn=poweradaptor_name).first().abbreviation
                if abbreviation_name in computer.inneraccessory :
                    inneraccessory_name = inneraccessory_name + poweradaptor_name
                    computer_weight +=  PnMap.query.filter_by(pn=poweradaptor_name).first().weight # Add weight for power adapter
                    poweradaptor_qty = poweradaptor_qty - computer_qty
        else:
            if form.dinrail.data != None : 
                dinrail_name = form.dinrail.data.pn
                dinrail_qty  = form.qty_dinrail.data  
            if form.dmpbr.data != None : 
                dmpbr_name = form.dmpbr.data.pn
                dmpbr_qty  = form.qty_dmpbr.data
            if form.fankit.data != None : 
                fankit_name = form.fankit.data.pn
                fankit_qty  = form.qty_fankit.data
            if form.wallmount.data != None : 
                wallmount_name = form.wallmount.data.pn
                wallmount_qty  = form.qty_wallmount.data
            if form.card1.data != None : 
                card1_name = form.card1.data.pn
                card1_qty  = form.qty_card1.data
            if form.card2.data != None : 
                card2_name = form.card2.data.pn
                card2_qty  = form.qty_card2.data
            if form.gpu.data != None : 
                gpu_name = form.gpu.data.pn
                gpu_qty  = form.qty_gpu.data
            if form.poweradaptor.data != None :
                poweradaptor_name = form.poweradaptor.data.pn
                poweradaptor_qty  = form.qty_poweradaptor.data
        if form.cablekit1.data != None :
            cablekit1_name = form.cablekit1.data.pn
            cablekit1_qty  = form.qty_cablekit1.data
        if form.cablekit2.data != None :
            cablekit2_name = form.cablekit2.data.pn
            cablekit2_qty  = form.qty_cablekit2.data
        if form.camera.data != None :
            camera_name = form.camera.data.pn
            camera_qty = form.qty_camera.data 
        #create packages    
        # name, w, t, h, weight
        packages =[]
        packages_computer =[]
        if computer_qty != 0 :
            name = computer_name
            if inneraccessory_name != None:
                name = name  + inneraccessory_name
            for i in range(computer_qty):
                package = Package(name, computer.width, computer.thickness, computer.height, computer_weight)
                packages_computer.append(package)    
        if dinrail_qty > 0 :
            name = dinrail_name
            dinrail_package = PnMap.query.filter_by(pn=dinrail_name).first()
            for i in range(1,dinrail_qty+1):
                package = Package(name, dinrail_package.width, dinrail_package.thickness, dinrail_package.height,dinrail_package.weight)
                packages.append(package)
        if dmpbr_qty > 0 :
            name = dmpbr_name
            dmpbr_package = PnMap.query.filter_by(pn=dmpbr_name).first()
            for i in range(1,dmpbr_package_qty+1):
                package = Package(name, dmpbr_package.width, dmpbr_package.thickness, dmpbr_package.height,dmpbr_package.weight)
                packages.append(package)
        if fankit_qty > 0 :
            name = fankit_name
            fankit_package = PnMap.query.filter_by(pn=fankit_name).first()
            package = Package(name, fankit_package.width, fankit_package.thickness, fankit_package.height,fankit_package.weight)
            for i in range(1,fankit_qty+1):
                package = Package(name, fankit_package.width, fankit_package.thickness, fankit_package.height,fankit_package.weight)
                packages.append(package)
        if wallmount_qty > 0 :
            name = wallmount_name
            wallmount_package = PnMap.query.filter_by(pn=wallmount_name).first()
            for i in range(1,wallmount_qty+1):
                package = Package(name, wallmount_package.width, wallmount_package.thickness, wallmount_package.height,wallmount_package.weight)
                packages.append(package)
        if card1_qty > 0 :
            name = card1_name
            card1_package = PnMap.query.filter_by(pn=card1_name).first()
            for i in range(1,card1_qty+1):
                package = Package(name, card1_package.width, card1_package.thickness, card1_package.height,card1_package.weight)
                packages.append(package)
        if card2_qty > 0 :
            name = card2_name
            card2_package = PnMap.query.filter_by(pn=card2_name).first()
            for i in range(1,card2_qty+1):
                package = Package(name, card2_package.width, card2_package.thickness, card2_package.height,card2_package.weight)
                packages.append(package)
        if gpu_qty > 0 :
            name = gpu_name
            gpu_package = PnMap.query.filter_by(pn=gpu_name).first()
            for i in range(1,gpu_qty+1):
                package = Package(name, gpu_package.width, gpu_package.thickness, gpu_package.height,gpu_package.weight)
                packages.append(package)
        if cablekit1_qty > 0 :
            name = cablekit1_name
            cablekit1_package = PnMap.query.filter_by(pn=cablekit1_name).first()
            for i in range(1,cablekit1_qty+1):
                package = Package(name, cablekit1_package.width, cablekit1_package.thickness, cablekit1_package.height,cablekit1_package.weight)
                packages.append(package)
        if cablekit2_qty > 0 :
            name = cablekit2_name
            cablekit2_package = PnMap.query.filter_by(pn=cablekit2_name).first()
            for i in range(1,cablekit2_qty+1):
                package = Package(name, cablekit2_package.width, cablekit2_package.thickness, cablekit2_package.height,cablekit2_package.weight)
                packages.append(package)
        if camera_qty > 0 :
            name = camera_name
            camera_package = PnMap.query.filter_by(pn=camera_name).first()
            for i in range(1,camera_qty+1):
                package = Package(name, camera_package.width, camera_package.thickness, camera_package.height,camera_package.weight)
                packages.append(package)
        if poweradaptor_qty > 0 :
            name = poweradaptor_name
            poweradaptor_package = PnMap.query.filter_by(pn=poweradaptor_name).first()
            for i in range(1,poweradaptor_qty+1):
                package = Package(name, poweradaptor_package.width, poweradaptor_package.thickness, poweradaptor_package.height,poweradaptor_package.weight)
                packages.append(package)

        if Boxes_SEMIL != [] or Boxes_RGS != []:
            platforms_b = {'Platform1':Boxes + Boxes_SEMIL + Boxes_RGS}
        else:
            platforms_b = {'Platform1':Boxes}
        all_pkgs = packages + packages_computer
        solutions,details,totalpercentage,packing_data = classifier(platforms_b, all_pkgs)

        # Strategy: if computers exist, try packing one set and compare
        if computer_qty > 0 and packages_computer:
            def ceil_div(a, b):
                return (a + b - 1) // b if b > 0 else 0
            # Build one_set: 1 computer + its share of accessories
            one_set = [packages_computer[0]]
            # Helper to create accessory package
            def add_acc(name, pn):
                if not pn:
                    return
                p = lookup_pn(pn)
                if p and p.width and p.height and p.thickness:
                    one_set.append(Package(pn, p.width, p.thickness, p.height, p.weight or 1))
            # Binary accessories (0 or 1 per computer)
            for q, n in [(dinrail_qty, dinrail_name), (dmpbr_qty, dmpbr_name),
                         (fankit_qty, fankit_name), (wallmount_qty, wallmount_name),
                         (poweradaptor_qty, poweradaptor_name)]:
                if q and q > 0 and n:
                    add_acc(n, n)
            # Multiple accessories (divided by computer_qty)
            for q, n in [(card1_qty, card1_name), (card2_qty, card2_name),
                         (gpu_qty, gpu_name), (cablekit1_qty, cablekit1_name),
                         (cablekit2_qty, cablekit2_name), (camera_qty, camera_name)]:
                cnt = ceil_div(q, computer_qty) if q and n else 0
                for _ in range(cnt):
                    add_acc(n, n)

            if len(one_set) > 1:
                sol_a, det_a, pct_a, pdata_a = classifier(platforms_b, one_set)
                if pdata_a and len(pdata_a) == 1 and computer_qty <= len(packing_data):
                    # Strategy A wins: repeat one_set box for each unit
                    packing_data = []
                    details = []
                    bd = pdata_a[0]
                    total_wt = 0
                    pkg_list = []
                    for acc in one_set:
                        total_wt += acc.get_weight()
                    solutions = [f"{bd['name']} | Packed: 100.00%",
                                 f"{bd['w']} x {bd['t']} x {bd['h']}inches | Total Weight | {total_wt:.2f}lbs"]
                    # Count items by name
                    from collections import Counter
                    name_counts = Counter(acc.get_name() for acc in one_set)
                    for name, cnt in name_counts.items():
                        wgt = sum(acc.get_weight() for acc in one_set if acc.get_name() == name)
                        solutions.append(f"{name} | {wgt:.2f}lbs x {cnt}")
                    # Use actual classifier output for positions/rotations
                    ref_box = pdata_a[0]
                    details.append(f"Details")
                    details.append(f"{bd['w']} x {bd['t']} x {bd['h']}inches | Total Weight | {total_wt:.2f}lbs")
                    for pkg in ref_box['packages']:
                        details.append(f"{pkg['name']} | {pkg['rot']} | {pkg['x']:.2f},{pkg['y']:.2f},{pkg['z']:.2f} | {pkg['ow']} x {pkg['ot']} x {pkg['oh']}inches | {pkg.get('weight', 0):.2f}lbs")
                    # Build packing_data for 3D view using actual classifier positions
                    for unit_idx in range(computer_qty):
                        pkgs_data = []
                        for pkg in ref_box['packages']:
                            pkgs_data.append({
                                'name': pkg['name'], 'x': pkg['x'], 'y': pkg['y'], 'z': pkg['z'],
                                'ow': pkg['ow'], 'ot': pkg['ot'], 'oh': pkg['oh'],
                                'rot': pkg['rot'],
                            })
                        packing_data.append({
                            'name': bd['name'],
                            'w': bd['w'], 't': bd['t'], 'h': bd['h'],
                            'packages': pkgs_data,
                        })
                    totalpercentage = 1.0
    else:
        packing_data = []
    # 1. Fetch your objects as you did before
    raw_products = (
        PnMap.query.filter_by(category='COMPUTER').order_by(PnMap.pn).all() + 
        PnMap.query.filter_by(category='PB').order_by(PnMap.pn).all() + 
        PnMap.query.filter_by(category='NRU').order_by(PnMap.pn).all() + 
        PnMap.query.filter_by(category='SEMIL').order_by(PnMap.pn).all()
        )

    # 2. Extract the 'pn' attribute from each object into a list of strings
    productlist = [item.pn for item in raw_products]
    products = []
    for x in productlist :
        pns = f"{x}"
        pns = pns.replace("('","")
        pns = pns.replace("',)","")
        products.append(pns)
    return render_template('packing.html', form=form, products=products, searched=searched,solutions=solutions, details=details, totalpercentage=totalpercentage, packing_data=packing_data, userrole=userrole)  

@main.route('/qualitylog', methods=['GET', 'POST'])
@login_required
def add_qualitylog():
    role = get_userrole(current_user.id)
    form = AddQualityLogForm()  
    if form.validate_on_submit():
        reportname = get_username(current_user.id)
        reporttime = datetime.datetime.now().strftime("%y/%m/%d %H:%M")
        processlog = reporttime + " " + reportname + " " + form.reason.data
        transaction = QualityLog(wo=form.wo.data.replace("/","-"), source= form.source.data, pn=str(form.pn.data), csn=str(form.csn.data), 
                    defectpart=form.defectpart.data,defectpartsn=form.defectpartsn.data,reason=form.reason.data,
                    status="New",reportid=current_user.id,reporttime = datetime.datetime.now(),
                    ownerid = -1,processlog=processlog,conclusion="", cause=None,
                    vendorname=form.vendorname.data or '', category=form.category.data or '',
                    nonconformingno=form.nonconformingno.data or '')
        db.session.add(transaction)
        db.session.commit()
        flash('Create Log successful')
    return render_template('add_qlog.html', form=form,  userrole=role) 

@main.route('/queryqlog', methods=['GET', 'POST'])
@login_required
def queryqlog():
    form = QueryQlogForm()
    searched = 0
    qlogs = []
    if request.method == "POST":
        return redirect(url_for('main.queryqlog', **{k: v for k, v in request.form.items() if v}))

    qlogs = QualityLog.query
    if request.args.get('startdate') and request.args.get('enddate'):
        try:
            sd = datetime.datetime.strptime(request.args['startdate'], '%Y-%m-%d')
            ed = datetime.datetime.strptime(request.args['enddate'], '%Y-%m-%d')
            if ed >= sd:
                qlogs = qlogs.filter(func.DATE(QualityLog.reporttime) >= func.DATE(sd),
                                     func.DATE(QualityLog.reporttime) <= func.DATE(ed))
                form.startdate.data = sd
                form.enddate.data = ed
        except: pass
    if request.args.get('status', 'All') != 'All':
        qlogs = qlogs.filter_by(status=request.args['status'])
        form.status.data = request.args['status']
    if request.args.get('source', 'All') != 'All':
        qlogs = qlogs.filter_by(source=request.args['source'])
        form.source.data = request.args['source']
    cat_val = request.args.get('category', '')
    if cat_val:
        qlogs = qlogs.filter(QualityLog.category == cat_val)
        form.category.data = cat_val
    for field in ['wo', 'pn', 'csn', 'defectpart', 'defectpartsn']:
        val = request.args.get(field, '')
        if val:
            qlogs = qlogs.filter(getattr(QualityLog, field).ilike('%' + val + '%'))
            getattr(form, field).data = val
    if any(request.args.values()):
        qlogs = qlogs.order_by(QualityLog.reporttime).all()
        searched = 1
    role = get_userrole(current_user.id)
    if role < 2:
        return redirect(url_for('main.display_workorders'))
    searchtable = []
    for qlog in qlogs :
        rows = []
        rows.append(qlog.id)
        rows.append(qlog.status)
        rows.append(qlog.source)
        rows.append(qlog.pn)
        rows.append(qlog.csn)
        rows.append(qlog.defectpart)
        rows.append(qlog.defectpartsn)
        rows.append(qlog.category or '')
        rows.append(qlog.reporttime.strftime("%y/%m/%d %H:%M"))
        rows.append(get_username(qlog.reportid))
        rows.append(get_username(qlog.ownerid))
        rows.append(qlog.reason)
        rows.append(qlog.conclusion)
        rows.append(qlog.cause)
        rows.append(qlog.nonconformingno or '')
        searchtable.append(rows)
    return render_template('queryqlog.html', form=form, userrole=role, searched=searched,searchtable=searchtable)

@main.route('/ViewEditQlog/<id>', methods=['GET', 'POST'])
@login_required
def ViewEditQlog(id): 
    print(id)
    qlog = QualityLog.query.filter_by(id=id)
    form = EditQualityLogForm(obj=qlog[0])
    role = get_userrole(current_user.id)
    #if request.method == 'GET' :
    #    qlogbackup = qlog[0]
    if form.validate_on_submit():
        # Not update product name
        #product.pn = form.pn.data
        qlog_org = QualityLog.query.filter_by(id=id)
        reportname = get_username(current_user.id)
        reporttime = datetime.datetime.now().strftime("%y/%m/%d %H:%M")
        processlog = qlog_org[0].processlog
        if(qlog_org[0].status!=form.status.data.strip()):
            processlog = processlog + "\n" + reporttime + " " + reportname + " Change status to " + form.status.data
        if(len(form.newaction.data.strip())):            
            processlog = qlog_org[0].processlog + "\n" + reporttime + " " + reportname + " " + form.newaction.data
        qlog_org[0].wo=form.wo.data.replace("/","-")
        qlog_org[0].source=form.source.data
        qlog_org[0].pn=str(form.pn.data)
        qlog_org[0].csn=str(form.csn.data), 
        qlog_org[0].defectpart=form.defectpart.data
        qlog_org[0].defectpartsn=form.defectpartsn.data
        qlog_org[0].reason=form.reason.data
        qlog_org[0].status=form.status.data
        qlog_org[0].ownerid=current_user.id #last modified by
        qlog_org[0].processlog=processlog
        qlog_org[0].conclusion=form.conclusion.data.strip()
        qlog_org[0].cause=form.cause.data.strip()
        qlog_org[0].nonconformingno=form.nonconformingno.data.strip() if form.nonconformingno.data else ''
        db.session.commit()
        flash('Update successful')
        #return redirect(session.get('previous_url','/'))
        #return redirect(url_for('main.queryproduct'))
    return render_template('edit_Qlog.html', form=form, id=id, userrole=role)

@main.route('/rma')
@login_required
def rma_list():
    if get_userrole(current_user.id) < 2: abort(403)
    role = get_userrole(current_user.id)
    status_filter = request.args.get('status', 'new')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    keywords = request.args.get('keywords', '')
    query = RmaCases.query.order_by(RmaCases.cstime.desc())
    if keywords:
        q = '%' + keywords + '%'
        query = query.filter(
            db.or_(
                RmaCases.ntarmano.ilike(q),
                RmaCases.customers.ilike(q),
                RmaCases.pn.ilike(q),
                RmaCases.csn.ilike(q),
                RmaCases.descriptionbycustomer.ilike(q),
                RmaCases.assetowner.ilike(q),
            )
        )
    if status_filter == 'all' and not start_date and not end_date and not keywords:
        ytd = datetime.datetime(datetime.datetime.now().year, 1, 1)
        query = query.filter(RmaCases.cstime >= ytd)
    else:
        if start_date:
            try:
                sd = datetime.datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(RmaCases.cstime >= sd)
            except: pass
        if end_date:
            try:
                ed = datetime.datetime.strptime(end_date, '%Y-%m-%d') + datetime.timedelta(days=1)
                query = query.filter(RmaCases.cstime < ed)
            except: pass
    if status_filter != 'all':
        query = query.filter(RmaCases.status == status_filter)
    cases = query.all()
    for c in cases:
        safe_cust = c.customers.replace('/', '_').replace('\\', '_')
        safe_pn = c.pn.replace('/', '_').replace('\\', '_')
        cnt = RmaCases.query.filter_by(ntarmano=c.ntarmano).count()
        c.file_base = f"00_Neousys_{c.ntarmano}_{safe_cust}_{safe_pn}_{cnt}Units"
        c.recvby = get_username(c.recvid) if c.recvid else ''
        c.processby = get_username(c.processid) if c.processid else ''
        c.shipment_count = c.shipments.filter_by(status='shipped').count()
        latest = c.shipments.filter_by(status='shipped').order_by(RmaVendorShipment.shiptovendortime.desc()).first()
        c.latest_shipment = latest
        c.shipby = get_username(latest.shiptovendorid) if (latest and latest.shiptovendorid) else ''
        c.recvfromvendorby = get_username(latest.recvfromvendorid) if (latest and latest.recvfromvendorid) else ''
        c.closeby = get_username(c.closeid) if c.closeid else ''
        if not c.assetowner:
            c.assetowner = c.customers
    counts = {
        'new': RmaCases.query.filter_by(status='new').count(),
        'received': RmaCases.query.filter_by(status='received').count(),
        'processing': RmaCases.query.filter_by(status='processing').count(),
        'waiting_for_shipping': RmaCases.query.filter_by(status='waiting_for_shipping').count(),
        'shipped_to_vendor': RmaCases.query.filter_by(status='shipped_to_vendor').count(),
        'closed': RmaCases.query.filter_by(status='closed').count(),
        'canceled': RmaCases.query.filter_by(status='canceled').count(),
    }
    # IW/OOW for closed cases (RMA page)
    closed_cases = RmaCases.query.filter_by(status='closed').all()
    iw = oow = 0
    for c in closed_cases:
        w = (c.warranty or '').strip().lower()
        if w in ('yes',) or '-' in w or '/' in w:
            iw += 1
        else:
            oow += 1
    counts['iw'] = iw
    counts['oow'] = oow
    return render_template('rma.html', cases=cases, counts=counts,
                           current_status=status_filter, userrole=role,
                           start_date=start_date, end_date=end_date,
                           keywords=keywords,
                           productlist=[p[0] for p in PnMap.query.with_entities(PnMap.pn).all()],
                           invparts={wh: [p.partsname for p in PartsInventory.query.filter_by(warehouse=wh).all()] for wh in ('WH10', 'WH12')})

def next_ntarmano():
    now = datetime.datetime.now()
    prefix = now.strftime('RNTA%y%m%d-')
    last = RmaCases.query.filter(
        RmaCases.ntarmano.like(prefix + '%')
    ).order_by(RmaCases.id.desc()).first()
    if last:
        seq = int(last.ntarmano.split('-')[-1]) + 1
    else:
        seq = 1
    return prefix + str(seq).zfill(3)


def generate_rma_files(case, csns=None):
    import zipfile, io, shutil
    from lxml import etree

    basedir = os.path.dirname(os.path.abspath(__file__))
    template = os.path.join(basedir, '../../rma_template.docx')
    outdir = os.path.join(basedir, '../static/rma')
    outdir = os.path.abspath(outdir)
    os.makedirs(outdir, exist_ok=True)
    safe_cust = case.customers.replace('/', '_').replace('\\', '_')
    safe_pn = case.pn.replace('/', '_').replace('\\', '_')
    base = f"00_Neousys_{case.ntarmano}_{safe_cust}_{safe_pn}_{len(csns) if csns else 1}Units"
    docx_path = os.path.join(outdir, base + '.docx')
    doc_path = os.path.join(outdir, base + '.doc')
    pdf_path = os.path.join(outdir, base + '.pdf')

    W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    XML_SPACE = '{http://www.w3.org/XML/1998/namespace}space'

    def visual_to_cell(cells, vis_col):
        span = 0
        for ci, cell in enumerate(cells):
            tc_pr = cell.find(f'{W}tcPr')
            n = 1
            if tc_pr is not None:
                gs = tc_pr.find(f'{W}gridSpan')
                if gs is not None and gs.get(f'{W}val'):
                    n = int(gs.get(f'{W}val'))
            if vis_col < span + n:
                return ci
            span += n
        return None

    def set_xml_cell(doc_xml, table_idx, row_idx, vis_col, text):
        root = etree.fromstring(doc_xml)
        tables = root.findall(f'.//{W}tbl')
        if table_idx >= len(tables):
            return doc_xml
        rows = tables[table_idx].findall(f'.//{W}tr')
        if row_idx >= len(rows):
            return doc_xml
        cells = rows[row_idx].findall(f'.//{W}tc')
        ci = visual_to_cell(cells, vis_col)
        if ci is None:
            return doc_xml
        for p in cells[ci].findall(f'.//{W}p'):
            runs = p.findall(f'.//{W}r')
            if runs:
                texts = runs[0].findall(f'.//{W}t')
                if texts:
                    texts[0].text = str(text)
                    texts[0].set(XML_SPACE, 'preserve')
                    return etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
            # No runs - create one
            r_elem = etree.SubElement(p, f'{W}r')
            t_elem = etree.SubElement(r_elem, f'{W}t')
            t_elem.text = str(text)
            t_elem.set(XML_SPACE, 'preserve')
            return etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
        return doc_xml

    def append_xml_cell(doc_xml, table_idx, row_idx, vis_col, text):
        root = etree.fromstring(doc_xml)
        tables = root.findall(f'.//{W}tbl')
        if table_idx >= len(tables):
            return doc_xml
        rows = tables[table_idx].findall(f'.//{W}tr')
        if row_idx >= len(rows):
            return doc_xml
        cells = rows[row_idx].findall(f'.//{W}tc')
        ci = visual_to_cell(cells, vis_col)
        if ci is None:
            return doc_xml
        all_paras = cells[ci].findall(f'.//{W}p')
        p = all_paras[1] if len(all_paras) > 1 else all_paras[0]
        r_elem = etree.SubElement(p, f'{W}r')
        t_elem = etree.SubElement(r_elem, f'{W}t')
        t_elem.text = str(text)
        t_elem.set(XML_SPACE, 'preserve')
        return etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)

    # Read template, modify XML directly
    with zipfile.ZipFile(template, 'r') as zin:
        doc_xml = zin.read('word/document.xml')
        now = datetime.datetime.now()
        doc_xml = append_xml_cell(doc_xml, 0, 0, 3, case.ntarmano)
        doc_xml = set_xml_cell(doc_xml, 0, 2, 1, now.strftime('%m/%d/%Y'))
        doc_xml = set_xml_cell(doc_xml, 0, 3, 1, case.customers)
        doc_xml = set_xml_cell(doc_xml, 0, 4, 1, case.shippingaddress or '')
        doc_xml = set_xml_cell(doc_xml, 0, 6, 1, case.rmacontactname or '')
        doc_xml = set_xml_cell(doc_xml, 0, 6, 5, case.rmacontactemail or '')
        doc_xml = set_xml_cell(doc_xml, 0, 7, 1, case.rmacontactphone or '')
        if case.rmacontactname1:
            doc_xml = set_xml_cell(doc_xml, 0, 8, 1, case.rmacontactname1)
            doc_xml = set_xml_cell(doc_xml, 0, 8, 5, case.rmacontactemail1 or '')
        if case.rmacontactphone1:
            doc_xml = set_xml_cell(doc_xml, 0, 9, 1, case.rmacontactphone1)
        csn_str = ', '.join(csns) if csns else case.csn
        doc_xml = set_xml_cell(doc_xml, 1, 1, 0, case.pn)
        doc_xml = set_xml_cell(doc_xml, 1, 1, 1, csn_str)
        doc_xml = set_xml_cell(doc_xml, 1, 1, 3, str(len(csns)) if csns else '1')
        if case.cstime:
            doc_xml = set_xml_cell(doc_xml, 1, 2, 0, case.cstime.strftime('%m/%d/%Y'))
        doc_xml = set_xml_cell(doc_xml, 1, 3, 0, case.descriptionbycustomer or '')

        # Write modified docx
        with zipfile.ZipFile(docx_path, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == 'word/document.xml':
                    zout.writestr(item, doc_xml)
                else:
                    zout.writestr(item, zin.read(item.filename))

    return base

def rma_back():
    ref = request.referrer or ''
    if 'rma_list' in ref or '/rma' in ref.split('?')[0]:
        return redirect(ref)
    return redirect(url_for('main.rma_list'))

@main.route('/rma/new', methods=['GET', 'POST'])
@login_required
def rma_new():
    if get_userrole(current_user.id) < 2: abort(403)
    if request.method == 'POST':
        csns = [c.strip() for c in request.form['csn'].replace('|', ' ').replace(',', ' ').split() if c.strip()]
        if not csns:
            flash('At least one CSN is required')
            return redirect(url_for('main.rma_new'))
        ntarmano = request.form['ntarmano']
        existing = RmaCases.query.filter(RmaCases.ntarmano == ntarmano, RmaCases.csn.in_(csns)).count()
        if existing:
            flash(f'Duplicate submission detected: {existing} record(s) already exist with this RMA#')
            return redirect(url_for('main.rma_list'))
        first_case = None
        for csn in csns:
            case = RmaCases(
                ntarmano=ntarmano,
                customers=request.form['customers'],
                pn=request.form['pn'],
                csn=csn,
                warranty=request.form.get('warranty', ''),
                descriptionbycustomer=request.form['description'],
                csid=current_user.id,
                cstime=datetime.datetime.now(),
                rmacontactname=request.form['contactname'],
                rmacontactemail=request.form['email'],
                rmacontactphone=request.form['phone'],
                shippingaddress=request.form.get('shippingaddress', ''),
                rmacontactname1=request.form.get('contactname1'),
                rmacontactemail1=request.form.get('email1'),
                rmacontactphone1=request.form.get('phone1'),
                special=request.form.get('special', ''),
                rmatype=request.form.get('rmatype', 'RMA'),
            )
            db.session.add(case)
            case.assetowner = case.customers
            if case.customers.strip().upper() == 'NTA':
                case.status = 'processing'
                case.processid = current_user.id
                case.startprocesstime = datetime.datetime.now()
            if first_case is None:
                first_case = case
        db.session.commit()
        base = generate_rma_files(first_case, csns)
        flash(f'RMA case created ({len(csns)} units). Files: {base}.doc / {base}.pdf')
        if first_case.customers.strip().upper() == 'NTA':
            return redirect(url_for('main.rma_list', status='processing'))
        return redirect(url_for('main.rma_list', status='new'))
    ntarmano = next_ntarmano()
    productlist = PnMap.query.with_entities(PnMap.pn).all()
    products = []
    for x in productlist:
        pns = str(x).replace("('", "").replace("',)", "")
        products.append(pns)
    return render_template('rma_form.html', case=None,
                           ntarmano=ntarmano,
                           userrole=get_userrole(current_user.id),
                           products=products)

@main.route('/rma/<int:id>/receive', methods=['POST'])
@login_required
def rma_receive(id):
    if get_userrole(current_user.id) < 2: abort(403)
    case = RmaCases.query.get_or_404(id)
    case.status = 'received'
    case.recvid = current_user.id
    case.recvtime = datetime.datetime.now()
    db.session.commit()
    return rma_back()

@main.route('/rma/<int:id>/wait-shipping', methods=['POST'])
@login_required
def rma_wait_shipping(id):
    if get_userrole(current_user.id) < 2: abort(403)
    case = RmaCases.query.get_or_404(id)
    vendorrmano = request.form.get('vendorrmano', '')
    vendorname = request.form.get('vendorname', '')
    shippn = request.form.get('shippn', '')
    partsn = request.form.get('partsn', '')
    category = request.form.get('category', '')
    rwo_wh = request.form.get('rwo_warehouse', '').strip().upper()
    rma_parts_pn = request.form.get('rma_parts_pn', '').strip()
    rma_part_sn = request.form.get('rma_part_sn', '').strip()
    inv_time = datetime.datetime.now().strftime('%m/%d/%Y %H:%M')
    if rwo_wh in ('WH01', 'WH10', 'WH12'):
        wh_msg = f"{rwo_wh} to WH04 at shipping, WH04 to {rwo_wh} at receiving"
        if shippn and partsn:
            existing = PartsInventory.query.filter_by(partsname=shippn, partsn=partsn).count()
            if existing:
                flash('Duplicate item in partsinventory, it is wrong', 'danger')
                return rma_back()
        if rwo_wh in ('WH10', 'WH12') and rma_parts_pn and rma_part_sn:
            for r in PartsInventory.query.filter_by(partsname=rma_parts_pn, partsn=rma_part_sn).all():
                r.warehouse = 'OUTOFSTOCK'
                entry = f"[{inv_time}]: used for {case.ntarmano} of {case.customers}"
                r.history = (r.history.rstrip() + '\n' + entry) if r.history else entry
        if shippn and partsn:
            hist = f"[{inv_time}]:from {case.ntarmano} of {case.customers},shipped with {vendorrmano}, replaced by {rma_parts_pn}/{rma_part_sn} from {rwo_wh}"
            db.session.add(PartsInventory(partsname=shippn, partsn=partsn, warehouse='WH04', history=hist))
        # create a new NTA RMA case representing the NTA<->vendor RMA (no docx)
        new_ntar = next_ntarmano()
        desc = f"Created for <RWO {case.ntarmano}>."
        new_case = RmaCases(
            ntarmano=new_ntar,
            customers='NTA',
            pn=shippn,
            csn=partsn,
            warranty='',
            descriptionbycustomer=desc,
            csid=current_user.id,
            cstime=datetime.datetime.now(),
            rmacontactname='NTA',
            rmacontactemail='nta.rma@neousys-tech.com',
            rmacontactphone='847-656-3298',
            shippingaddress='55 E Hintz Rd, Wheeling, IL 60090',
            rmatype='RMA',
        )
        new_case.assetowner = 'NTA'
        new_case.status = 'waiting_for_shipping'
        db.session.add(new_case)
        db.session.flush()
        new_shipment = RmaVendorShipment(
            rma_case_id=new_case.id,
            vendorrmano=vendorrmano,
            shippn=shippn,
            partsn=partsn,
            vendorname=vendorname,
            category=category,
            assetowner='NTA',
            shiptovendortime=datetime.datetime.now(),
            shiptovendorid=current_user.id,
            warehousetransfer=wh_msg,
        )
        db.session.add(new_shipment)
    else:
        case.status = 'waiting_for_shipping'
        if vendorrmano or shippn or partsn or vendorname:
            active = case.shipments.order_by(RmaVendorShipment.id.desc()).first()
            if active and active.status != 'received':
                active.vendorrmano = vendorrmano
                active.shippn = shippn
                active.partsn = partsn
                active.vendorname = vendorname
                active.category = category
                active.assetowner = case.customers
                active.warehousetransfer = ''
                active.shiptovendortime = datetime.datetime.now()
                active.shiptovendorid = current_user.id
            else:
                ao = case.customers
                shipment = RmaVendorShipment(rma_case_id=case.id, vendorrmano=vendorrmano, shippn=shippn, partsn=partsn, assetowner=ao, vendorname=vendorname, category=category,
                                             shiptovendortime=datetime.datetime.now(), shiptovendorid=current_user.id, warehousetransfer='')
                db.session.add(shipment)
                case.assetowner = ao
    db.session.commit()
    return rma_back()

@main.route('/rma/<int:id>/delete', methods=['POST'])
@login_required
def rma_delete(id):
    if get_userrole(current_user.id) < 2: abort(403)
    case = RmaCases.query.get_or_404(id)
    if case.status == 'new':
        case.status = 'canceled'
        db.session.commit()
    return rma_back()

@main.route('/rma/<int:id>/hard-delete', methods=['POST'])
@login_required
def rma_hard_delete(id):
    if get_userrole(current_user.id) < 2: abort(403)
    case = RmaCases.query.get_or_404(id)
    if case.status == 'new':
        RmaVendorShipment.query.filter_by(rma_case_id=case.id).delete()
        db.session.delete(case)
        db.session.commit()
    return rma_back()

@main.route('/rma/<int:id>/unreceive', methods=['POST'])
@login_required
def rma_unreceive(id):
    if get_userrole(current_user.id) < 2: abort(403)
    case = RmaCases.query.get_or_404(id)
    if case.status == 'received':
        case.status = 'new'
        case.recvid = None
        case.recvtime = None
        db.session.commit()
    return rma_back()

@main.route('/rma/<int:id>/start', methods=['POST'])
@login_required
def rma_start(id):
    if get_userrole(current_user.id) < 2: abort(403)
    case = RmaCases.query.get_or_404(id)
    case.status = 'processing'
    case.processid = current_user.id
    case.startprocesstime = datetime.datetime.now()
    db.session.commit()
    return rma_back()

@main.route('/rma/<int:id>/create-wo', methods=['POST'])
@login_required
def rma_create_wo(id):
    if get_userrole(current_user.id) < 2: abort(403)
    case = RmaCases.query.get_or_404(id)
    wo_num = request.form.get('wo', case.ntarmano).replace('/', '-')
    exists = WorkOrder.query.filter_by(wo=wo_num, csn=case.csn).first()
    if exists:
        flash(f'WorkOrder {wo_num} already exists for CSN {case.csn}')
        return rma_back()
    wo = WorkOrder(
        wo=wo_num, customers=case.customers, pn=case.pn, csn=case.csn,
        cputype='', memorysize='', disksize='',
        cpuinstall=False, memoryinstall=False, gpuinstall=False,
        wifiinstall=False, caninstall=False, mezioinstall=False, fg5ginstall=False,
        gpu='', withwifi=False, withcan=False, withfg5g=False,
        ospreinstalled=False, osactivation=False, diskpreinstalled=False,
        osinstall='', packgo=False,
        asid=-1, insid=-1, astime=None, intime=None, tktime=None,
        csid=current_user.id, cstime=datetime.datetime.now(),
        ldtime=None, status=0, doc_items='')
    db.session.add(wo)
    db.session.commit()
    flash(f'WorkOrder {wo_num} created for {case.customers}')
    return rma_back()

@main.route('/rma/<int:id>/save-notes', methods=['POST'])
@login_required
def rma_save_notes(id):
    if get_userrole(current_user.id) < 2: abort(403)
    case = RmaCases.query.get_or_404(id)
    data = request.get_json()
    case.notes = data.get('notes', '')
    db.session.commit()
    return {'ok': True}

@main.route('/rma/<int:id>/unprocess', methods=['POST'])
@login_required
def rma_unprocess(id):
    if get_userrole(current_user.id) < 2: abort(403)
    case = RmaCases.query.get_or_404(id)
    if case.status == 'processing':
        case.status = 'received'
        case.processid = None
        case.startprocesstime = None
        db.session.commit()
    return rma_back()

@main.route('/rma/<int:id>/unwait', methods=['POST'])
@login_required
def rma_unwait(id):
    if get_userrole(current_user.id) < 2: abort(403)
    case = RmaCases.query.get_or_404(id)
    if case.status == 'waiting_for_shipping':
        case.status = 'processing'
        db.session.commit()
    return rma_back()

@main.route('/rma/<int:id>/unshipped', methods=['POST'])
@login_required
def rma_unshipped(id):
    if get_userrole(current_user.id) < 2: abort(403)
    case = RmaCases.query.get_or_404(id)
    if case.status == 'shipped_to_vendor':
        case.status = 'waiting_for_shipping'
        db.session.commit()
    return rma_back()

@main.route('/rma/<int:id>/unrecv-vendor', methods=['POST'])
@login_required
def rma_unrecv_vendor(id):
    if get_userrole(current_user.id) < 2: abort(403)
    case = RmaCases.query.get_or_404(id)
    if case.status == 'processing':
        s = case.shipments.filter_by(status='received').order_by(RmaVendorShipment.recvfromvendortime.desc()).first()
        if s:
            s.recvfromvendortime = None
            s.recvfromvendorid = None
            s.status = 'shipped'
        case.status = 'shipped_to_vendor'
        db.session.commit()
    return rma_back()

@main.route('/rma/<int:id>/ship-vendor', methods=['POST'])
@login_required
def rma_ship_vendor(id):
    if get_userrole(current_user.id) < 2: abort(403)
    case = RmaCases.query.get_or_404(id)
    if case.status != 'waiting_for_shipping':
        flash('Case is not in Wait Shipping state', 'danger')
        return rma_back()
    case.status = 'shipped_to_vendor'
    shippn = request.form.get('shippn', '') or ''
    partsn = request.form.get('partsn', '') or ''
    vendorname = request.form.get('vendorname', '')
    category = request.form.get('category', '')
    vendorrmano = request.form.get('vendorrmano', '')

    asset_owner = case.customers
    shipment = case.shipments.filter_by(status='shipped').order_by(RmaVendorShipment.id.desc()).first()
    if shipment:
        shipment.vendorrmano = vendorrmano
        shipment.shippn = shippn
        shipment.partsn = partsn
        shipment.vendorname = vendorname
        shipment.category = category
        shipment.shiptovendortime = datetime.datetime.now()
        shipment.shiptovendorid = current_user.id
        shipment.status = 'shipped'
    else:
        shipment = RmaVendorShipment(
            rma_case_id=case.id,
            vendorrmano=vendorrmano,
            shippn=shippn,
            partsn=partsn,
            vendorname=vendorname,
            category=category,
            shiptovendortime=datetime.datetime.now(),
            shiptovendorid=current_user.id,
            assetowner=asset_owner,
        )
        db.session.add(shipment)

    db.session.commit()
    return rma_back()

@main.route('/rma/<int:id>/recv-vendor', methods=['POST'])
@login_required
def rma_recv_vendor(id):
    if get_userrole(current_user.id) < 2: abort(403)
    case = RmaCases.query.get_or_404(id)
    shipment = case.shipments.filter_by(status='shipped').order_by(RmaVendorShipment.shiptovendortime.desc()).first()
    if shipment:
        shipment.recvfromvendortime = datetime.datetime.now()
        shipment.recvfromvendorid = current_user.id
        shipment.status = 'received'
    case.status = 'processing'
    db.session.commit()
    flash('Vendor shipment received, case returned to processing')
    return rma_back()

@main.route('/rma/<int:id>/close', methods=['POST'])
@login_required
def rma_close(id):
    if get_userrole(current_user.id) < 2: abort(403)
    case = RmaCases.query.get_or_404(id)
    case.conclusion = request.form['conclusion']
    case.notes = request.form.get('notes', '')
    case.status = 'closed'
    case.closetime = datetime.datetime.now()
    case.closeid = current_user.id
    if request.form.get('report_quality_close'):
        source = 'Production Line' if case.customers.upper() == 'NTA' else 'RMA'
        ql = QualityLog(
            source=source,
            wo=case.ntarmano,
            pn=case.pn,
            csn=case.csn,
            defectpart=case.pn,
            defectpartsn=case.csn,
            reason=(case.descriptionbycustomer or '')[:1000],
            status='New',
            reportid=current_user.id,
            reporttime=datetime.datetime.now(),
            ownerid=current_user.id,
            processlog='',
            conclusion=None,
            cause=None,
            vendorname='',
            category='',
        )
        db.session.add(ql)
    db.session.commit()
    return rma_back()

@main.route('/rma/<int:id>/recv-close', methods=['POST'])
@login_required
def rma_recv_close(id):
    if get_userrole(current_user.id) < 2: abort(403)
    case = RmaCases.query.get_or_404(id)
    shipment = case.shipments.filter_by(status='shipped').order_by(RmaVendorShipment.shiptovendortime.desc()).first()
    if shipment:
        shipment.recvfromvendortime = datetime.datetime.now()
        shipment.recvfromvendorid = current_user.id
        shipment.status = 'received'
        if shipment.shippn:
            inv_time = datetime.datetime.now().strftime('%m/%d/%Y %H:%M')
            inv_rows = PartsInventory.query.filter_by(partsname=shipment.shippn, partsn=shipment.partsn).all()
            if not inv_rows:
                inv_rows = PartsInventory.query.filter(
                    PartsInventory.partsname == shipment.shippn,
                    PartsInventory.warehouse == 'WH04',
                    PartsInventory.history.ilike('%' + case.ntarmano + '%'),
                ).all()
            for r in inv_rows:
                m = re.search(r'from\s+(WH\d+)', r.history or '')
                if m:
                    r.warehouse = m.group(1)
                entry = f"[{inv_time}] received from {shipment.vendorrmano or ''} of {shipment.vendorname or ''}"
                r.history = (r.history.rstrip() + '\n' + entry) if r.history else entry
    case.conclusion = request.form['conclusion']
    case.notes = request.form.get('notes', '')
    m_rwo = re.search(r'<RWO\s+([^>]+)>', case.descriptionbycustomer or '')
    if m_rwo:
        orig_ntar = m_rwo.group(1).strip()
        orig = RmaCases.query.filter(RmaCases.ntarmano == orig_ntar).first()
        if orig:
            orig.conclusion = case.conclusion
    vendorname = request.form.get('vendorname_close', '').strip()
    if vendorname and shipment:
        shipment.vendorname = vendorname
    case.status = 'closed'
    case.closetime = datetime.datetime.now()
    case.closeid = current_user.id
    if request.form.get('report_quality_close'):
        source = 'Production Line' if case.customers.upper() == 'NTA' else 'RMA'
        ql = QualityLog(
            source=source,
            wo=case.ntarmano,
            pn=case.pn,
            csn=case.csn,
            defectpart=shipment.shippn if shipment else '',
            defectpartsn=shipment.partsn if shipment else '',
            reason=(case.descriptionbycustomer or '')[:1000],
            status='New',
            reportid=current_user.id,
            reporttime=datetime.datetime.now(),
            ownerid=current_user.id,
            processlog='',
            conclusion=None,
            cause=None,
            vendorname=shipment.vendorname if shipment else '',
            category='',
        )
        db.session.add(ql)
    db.session.commit()
    flash('Received from vendor and closed RMA case')
    return rma_back()

@main.route('/rma/download/<filename>')
@login_required
def rma_download(filename):
    if get_userrole(current_user.id) < 2: abort(403)
    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../static/rma')
    outdir = os.path.abspath(outdir)
    return send_from_directory(outdir, filename)

@main.route('/rma/export')
@login_required
def rma_export():
    if get_userrole(current_user.id) < 2: abort(403)
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    keywords = request.args.get('keywords', '')
    query = RmaCases.query.order_by(RmaCases.cstime.desc())
    if keywords:
        q = '%' + keywords + '%'
        query = query.filter(
            db.or_(
                RmaCases.ntarmano.ilike(q),
                RmaCases.customers.ilike(q),
                RmaCases.pn.ilike(q),
                RmaCases.csn.ilike(q),
                RmaCases.descriptionbycustomer.ilike(q),
                RmaCases.assetowner.ilike(q),
            )
        )
    if start_date:
        try:
            query = query.filter(RmaCases.cstime >= datetime.datetime.strptime(start_date, '%Y-%m-%d'))
        except: pass
    if end_date:
        try:
            query = query.filter(RmaCases.cstime < datetime.datetime.strptime(end_date, '%Y-%m-%d') + datetime.timedelta(days=1))
        except: pass
    cases = query.all()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['RMA#', 'Customer', 'PN', 'CSN', 'Description', 'Created', 'Status',
                 'Contact', 'Email', 'Phone', 'Shipping Address',
                 'Received', 'Recv By', 'Processed', 'Process By',
                 'Shipped to Vendor', 'Ship By', 'Vendor RMA#',
                 'Recv from Vendor', 'Vendor Recv By',
                 'Closed', 'Closed By', 'Conclusion', 'Notes'])
    for c in cases:
        cw.writerow([c.ntarmano, c.customers, c.pn, c.csn, c.descriptionbycustomer,
                     c.cstime, c.status,
                     c.rmacontactname, c.rmacontactemail, c.rmacontactphone, c.shippingaddress,
                     c.recvtime, get_username(c.recvid) if c.recvid else '',
                     c.startprocesstime, get_username(c.processid) if c.processid else '',
                     c.shiptovendortime, get_username(c.shiptovendorid) if c.shiptovendorid else '',
                     c.vendorrmano,
                     c.recvfromvendortime, get_username(c.recvfromvendorid) if c.recvfromvendorid else '',
                     c.closetime, get_username(c.closeid) if c.closeid else '',
                     c.conclusion, c.notes])
    out = si.getvalue()
    si.close()
    return Response(out, mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment;filename=rmacases_{datetime.datetime.now().strftime("%y%m%d")}.csv'})

