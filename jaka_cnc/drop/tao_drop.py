# Builds jamaguchi_cnc1_drop.txt from jamaguchi_cnc36.txt: P7 Case1 (DI53/DO53) = drop the
# unloaded part at an outside point. Also builds two SIMULATION-ONLY tests.
# usage: python tao_drop.py ../jamaguchi_cnc36.txt .
import re, sys
src, outdir = sys.argv[1], sys.argv[2]
L = open(src).read().replace('\r','').split('\n')
def dd(l):
    t=l.split('#')[0].strip()
    if re.match(r'^(if|while)\s*\(',t): return 1
    if t=='end': return -1
    return 0
def blk(i):
    d=0
    for j in range(i,len(L)):
        d+=dd(L[j])
        if d==0: return i,j
def ok(lines,name):
    d=0
    for x in lines:
        d+=dd(x); assert d>=0,name
    assert d==0,name
    assert not any(re.search(r'"[^"]*[()][^"]*"',x) for x in lines),name
def find(pred,start=0):
    r=[i for i in range(start,len(L)) if pred(L[i])]; assert r; return r[0]

# ---------- 1. drop point declarations (after the P7 segment arrays) ----------
i=find(lambda l:l.startswith('p_process7_unload_segment_max ='))
p7=[x for x in L if x.startswith('p_process7_unload =')][0].split('=',1)[1].strip()
decl=['',
'# ===== [DROP] P7 Case1 = drop the part unloaded from CNC1 at an outside point =====',
'# Drop point taught 2026-11-18 (usrfr_thanh + tool_thanh): TCP X -112.925, Y 1317.358, Z 353.706,',
'# RX -86.283, RY -48.285, RZ -2.003. Tool Unload holding the part at the release height.',
'p_drop = [-9.049,127.295,101.570,128.230,-234.974,129.924]',
'# Approach / lift height: +100 mm Z. pose_add adds XYZ directly (same frame as kine_forward) and',
'# keeps the orientation (R_res = R_offset * R_pose, R_offset = identity), so this is straight up.',
'p_drop_up_offset = [0.0,0.0,100.0,0.0,0.0,0.0]',
'p_drop_pose = kine_forward(p_drop)',
'p_drop_above_pose = pose_add(p_drop_pose,p_drop_up_offset)',
'p_drop_above_joint = kine_inverse(p_drop,p_drop_above_pose)',
'drop_ok = 0']
L[i+1:i+1]=decl

# ---------- 2. P7 Case1 motion ----------
a=[k for k,l in enumerate(L) if l.strip()=='if(active_process == 7):']
a=[k for k in a if 'if(active_case == 52):' in L[k+1]][0]
a,b=blk(a)
ind=L[a][:len(L[a])-len(L[a].lstrip())]
s=ind+'        '
guard=['# Safety check: the lift offset must be +100 mm straight up (Z), X/Y unchanged.',
'# If pose_add works in another frame the drop is skipped instead of moving the wrong way.',
'drop_ok = 1',
'if(p_drop_above_pose[2] < p_drop_pose[2] + 90.0):','    drop_ok = 0','end',
'if(p_drop_above_pose[2] > p_drop_pose[2] + 110.0):','    drop_ok = 0','end',
'if(p_drop_above_pose[0] > p_drop_pose[0] + 5.0):','    drop_ok = 0','end',
'if(p_drop_above_pose[0] < p_drop_pose[0] - 5.0):','    drop_ok = 0','end',
'if(p_drop_above_pose[1] > p_drop_pose[1] + 5.0):','    drop_ok = 0','end',
'if(p_drop_above_pose[1] < p_drop_pose[1] - 5.0):','    drop_ok = 0','end',
'if(drop_ok == 0):','    case_motion_ok = 0','    log_message(2,"P7C1 DROP SKIPPED LIFT OFFSET IS NOT STRAIGHT UP CHECK POSE_ADD")','end']
body=['log_message(1,"CURRENT P7 CASE1 DROP OUTSIDE RUN")']+guard+[
'if(case_motion_ok == 1):',
'    log_message(1,"P7C1 MOVEJ HOMELOCATION START")',
'    movj(p_home_location,0,speed_movej_fast,720,0)',
'    log_message(1,"P7C1 HOMELOCATION COMPLETE")',
'    log_message(1,"P7C1 MOVEJ DROP ABOVE START")',
'    movj(p_drop_above_joint,0,speed_movej_fast,720,0)',
'    log_message(1,"P7C1 DROP ABOVE COMPLETE")',
'    log_message(1,"P7C1 MOVEL DOWN TO DROP START")',
'    movl(p_drop_pose,0,speed_movel,200,0)',
'    log_message(1,"P7C1 DROP COMPLETE")',
'    set_digital_output(4,64,1,1)',
'    log_message(1,"P7C1 DO65 ON WAIT DI65 ON UNCLAMP TOOL UNLOAD")',
'    di65 = get_digital_input(4,64)',
'    while(di65 == 0):','        sleep(0.1)','        di65 = get_digital_input(4,64)','    end',
'    set_digital_output(4,64,0,1)',
'    log_message(1,"P7C1 DI65 ON DO65 OFF UNCLAMP COMPLETE")',
'    log_message(1,"P7C1 MOVEL LIFT Z 100 START")',
'    movl(p_drop_above_pose,0,speed_movel_fast,3500,0)',
'    log_message(1,"P7C1 LIFT Z 100 COMPLETE")',
'    log_message(1,"P7C1 MOVEJ HOMELOCATION START")',
'    movj(p_home_location,0,speed_movej_fast,720,0)',
'    log_message(1,"P7C1 END AT HOMELOCATION")',
'else:',
'    set_digital_output(4,64,0,1)',
'    log_message(2,"P7C1 ABORTED DO65 OFF")',
'end']
ok(body,'p7')
L[a:b+1]=[ind+'if(active_process == 7):',ind+'    if(active_case == 52):']+[s+x for x in body]+[ind+'    end',ind+'end']

# ---------- 3. Home: recognise the drop segment instead of the old P7 segment ----------
h0=find(lambda l:'# Recognize any stopped position between Process7Unload and its Wait point.' in l)
h1=find(lambda l:l.strip()=='if(home_process7_unload_segment == 1):',h0)
ind=L[h0][:len(L[h0])-len(L[h0].lstrip())]
seg=['# [DROP] Recognize any stopped position between the drop point and the point 100 mm above it.',
'# A joint is outside when it is beyond BOTH endpoints by more than 5 degrees.',
'home_process7_unload_segment = 1']
for j in range(6):
    seg+=['if(home_actual_joint[%d] < p_drop[%d] - 5.0):'%(j,j),'    if(home_actual_joint[%d] < p_drop_above_joint[%d] - 5.0):'%(j,j),
          '        home_process7_unload_segment = 0','    end','end',
          'if(home_actual_joint[%d] > p_drop[%d] + 5.0):'%(j,j),'    if(home_actual_joint[%d] > p_drop_above_joint[%d] + 5.0):'%(j,j),
          '        home_process7_unload_segment = 0','    end','end']
ok(seg,'seg')
L[h0:h1]=[ind+x for x in seg]
k=find(lambda l:'log_message(1,"HOME ACTUAL POSITION IN PROCESS7UNLOAD SEGMENT")' in l)
L[k]=L[k].replace('IN PROCESS7UNLOAD SEGMENT','IN DROP SEGMENT')
r=find(lambda l:'log_message(1,"HOME ROUTE PROCESS7UNLOAD SEGMENT TO PROCESS7UNLOADWAIT")' in l)
ind=L[r][:len(L[r])-len(L[r].lstrip())]
assert L[r+1].strip()=='movj(p_process7_unload_wait,0,speed_movej_fast,720,0)'
assert L[r+3].strip()=='log_message(1,"HOME ROUTE PROCESS7UNLOADWAIT COMPLETE")'
L[r]=ind+'log_message(1,"HOME ROUTE DROP SEGMENT MOVEL STRAIGHT UP TO DROP ABOVE")'
L[r+1]=ind+'movl(p_drop_above_pose,0,30,200,0)'
L[r+3]=ind+'log_message(1,"HOME ROUTE DROP ABOVE COMPLETE")'
L.insert(0,'# [DROP] Separate program: CNC1 cycle (P2) + P7 Case1 drops the unloaded part outside.')
ok(L,'main')
assert 'p_process7_unload_wait' not in '\n'.join(x.split('#')[0] for x in L[L.index(decl[1]):]), 'old P7 point still used'
open(outdir+'/jamaguchi_cnc1_drop.txt','w',newline='').write('\r\n'.join(L))

# ---------- 4. simulation tests ----------
he=[k for k,l in enumerate(L) if l.startswith('# Reset common and Process interlock outputs')][0]
header=L[1:he]
def stub(lines):
    out=[];skip=0
    for l in lines:
        if skip: skip+=dd(l); continue
        sp=l[:len(l)-len(l.lstrip())]; t=l.strip()
        if re.match(r'^while\(di\d+ == 0\):$',t): skip=1; continue
        if t.startswith('set_digital_output('): out.append(sp+'sleep(0.01)'); continue
        m=re.match(r'^(di\d+) = get_digital_input\(4,(\d+)\)$',t)
        if m: out+= [sp+'log_message(1,"SIM SKIP WAIT DI%d")'%(int(m.group(2))+1), sp+'sleep(0.3)']; continue
        l=l.replace('get_analog_input(4,15)','sim_ai16')
        assert 'get_digital_input' not in l and 'wait_input' not in l, l
        out.append(l)
    return out
def dedent(x):
    n=min(len(y)-len(y.lstrip()) for y in x if y.strip()); return [y[n:] if y.strip() else '' for y in x]
a=[k for k,l in enumerate(L) if l.strip()=='if(active_process == 7):' and 'if(active_case == 52):' in L[k+1]][0]
a,b=blk(a)
WARN=['# !!! SIMULATION ONLY !!! Generated from jamaguchi_cnc1_drop.txt; DO writes and DI waits removed.','']
t1=WARN+header+['','log_message(1,"SIM DROP TEST START")','movj(p_door_c1,0,speed_movej_fast,720,0)',
 'active_process = 7','active_case = 52','case_motion_ok = 1']+stub(dedent(L[a:b+1]))+['log_message(1,"SIM DROP TEST END")','']
ok(t1,'t1'); open(outdir+'/sim_drop_test.txt','w',newline='').write('\r\n'.join(t1))
h0=[k for k,l in enumerate(L) if l.strip()=='home_actual_joint = get_atl_joint_pose()'][0]
h1=[k for k,l in enumerate(L) if 'DO16 ON ROBOT AT HOME WAIT DI90 OFF' in l][0]
home=stub(dedent(L[h0:h1+2]))
t2=WARN+header+['','log_message(1,"SIM DROP HOME TEST START")','sim_ai16 = 1',
 'sim_mid_pose = pose_add(p_drop_pose,[0.0,0.0,50.0,0.0,0.0,0.0])']
for k,(n,mv) in enumerate([('AT DROP POINT','movl(p_drop_pose,0,50,200,0)'),('50 MM ABOVE DROP','movl(sim_mid_pose,0,50,200,0)')],1):
    t2+=['movj(p_home_location,0,speed_movej_fast,720,0)','movj(p_drop_above_joint,0,speed_movej_fast,720,0)',mv,
         'home_route_door_done = 0','home_already_home = 0','home_route_hint = 0',
         'log_message(1,"SIM DROP HOME %d %s EXPECT IN DROP SEGMENT THEN MOVEL UP THEN HOME")'%(k,n)]+home
t2+=['log_message(1,"SIM DROP HOME TEST END")','']
ok(t2,'t2'); open(outdir+'/sim_drop_home_test.txt','w',newline='').write('\r\n'.join(t2))
print('main',len(L),'| sim_drop',len(t1),'| sim_drop_home',len(t2))
