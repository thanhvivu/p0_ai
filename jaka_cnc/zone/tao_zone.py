# Generates zone_monitor.txt (Sub-thread program), sim_zone_monitor.txt and sim_zone_test.txt.
# Uses only syntax verified on this controller: &&, elif, arithmetic assignment wrapped in ( ).
# usage: python tao_zone.py ../jamaguchi_cnc36.txt .
import re, sys
main_src, outdir = sys.argv[1], sys.argv[2]
init=['# X_user / Y_user = TCP converted from Base to usrfr_thanh [345.833,-489.782,-136.233, Rz 45.114].',
'# Thresholds (usrfr_thanh, tool_thanh): DoorC1 X 679.362, DoorC2 X -365.358, Pick Y 1237.165 - 50.',
'zone_door_margin = 20.0',
'zone_x1 = (679.362 + zone_door_margin)',
'zone_x2 = (-365.358 - zone_door_margin)',
'zone_y_pick_limit = 1187.165',
'zone_odd_last = -1','zone_even_last = -1','zone_pick_last = -1']
check=['zone_t = get_atl_tcp_pose()',
'zone_xu = (0.7056980154 * (zone_t[0] - 345.833) + 0.7085118376 * (zone_t[1] + 489.782) + 0.0011344638 * (zone_t[2] + 136.233))',
'zone_yu = (-0.7085100607 * (zone_t[0] - 345.833) + 0.7056988446 * (zone_t[1] + 489.782) - 0.0016231544 * (zone_t[2] + 136.233))',
'zone_odd = 0','zone_even = 0','zone_pick = 0',
'if(zone_xu > zone_x1):','    zone_odd = 1','end',
'if(zone_xu < zone_x2):','    zone_even = 1','end',
'if(zone_yu > zone_y_pick_limit):','    zone_pick = 1','end',
'# Write a DO only when its state changes, with a log line.']
for var,last,idx,name in [('zone_odd','zone_odd_last',55,'DO56 ODD CNC ZONE'),('zone_even','zone_even_last',56,'DO57 EVEN CNC ZONE'),('zone_pick','zone_pick_last',57,'DO58 PICK ZONE')]:
    check+=['if(%s == 1 && %s != 1):'%(var,last),'    set_digital_output(4,%d,1,1)'%idx,'    log_message(1,"%s ON")'%name,
            'elif(%s == 0 && %s != 0):'%(var,last),'    set_digital_output(4,%d,0,1)'%idx,'    log_message(1,"%s OFF")'%name,
            'end','%s = %s'%(last,var)]
def ok(lines):
    d=0
    for x in lines:
        t=x.split('#')[0].strip()
        if re.match(r'^(if|while)\s*\(',t): d+=1
        elif t=='end': d-=1
        assert d>=0
    assert d==0 and not any(re.search(r'log_message\(\d,"[^"]*[()][^"]*"',x) for x in lines)
    assert not any(re.match(r'^\s*[a-z_0-9\[\]]+ = [^(\[].*[-+*/] ',x) for x in lines), 'unparenthesized arithmetic'
mon=['# ZONE_MONITOR - run as Sub-thread1 from the main program. No motion commands.',
'# DO56 = TCP past DoorC1 + margin (odd CNC side), DO57 = past DoorC2 + margin (even CNC side),',
'# DO58 = TCP within 50 mm of the Pick point along Y_user or beyond. Warning only, not safety.']+init+[
'log_message(1,"ZONE MONITOR STARTED MARGIN 20 PICK Y 1187")','while(1):']+['    '+x for x in check]+['    sleep(0.05)','end','']
ok(mon); open(outdir+'/zone_monitor.txt','w',newline='').write('\r\n'.join(mon))
simmon=['# !!! SIMULATION ONLY !!! zone_monitor without DO writes; run as Sub-thread1 next to sim_main_simple.']+[
    (x[:len(x)-len(x.lstrip())]+'sleep(0.01)') if x.strip().startswith('set_digital_output(') else x for x in mon]
ok(simmon); open(outdir+'/sim_zone_monitor.txt','w',newline='').write('\r\n'.join(simmon))
L=open(main_src).read().replace('\r','').split('\n')
he=[i for i,l in enumerate(L) if l.startswith('# Reset common and Process interlock outputs')][0]
stub=lambda ls:[(x[:len(x)-len(x.lstrip())]+'sleep(0.01)') if x.strip().startswith('set_digital_output(') else x for x in ls]
tests=[('p_home_location','HOMELOCATION','ALL OFF'),('p_pick_true_axis','PICKWAIT','DO58 ON IF WITHIN 50 MM'),
 ('p_pick','PICK','DO58 ON'),('p_home_location','HOMELOCATION','DO58 OFF'),
 ('p_door_c1','DOORC1','DO56 OFF'),('p_odd_load_wait','C1LOADWAIT','DO56 ON'),('p_odd_load','C1LOAD','DO56 ON'),
 ('p_door_c1','DOORC1','DO56 OFF'),('p_door_c2','DOORC2','DO57 OFF'),('p_even_load_wait','LOADM2_WAIT','DO57 ON'),
 ('p_even_load','LOADC2','DO57 ON'),('p_home_location','HOMELOCATION','ALL OFF')]
t=['# !!! SIMULATION ONLY !!! zone check after each move; DO writes replaced by sleep, ON/OFF logs kept.','']+L[:he]+['']+init+['log_message(1,"SIM ZONE TEST START")']
for k,(p,n,e) in enumerate(tests,1):
    t+=['log_message(1,"SIM ZONE %d AT %s EXPECT %s")'%(k,n,e),'movj(%s,0,speed_movej_fast,720,0)'%p]+stub(check)
t+=['log_message(1,"SIM ZONE TEST END")','']
ok(t); open(outdir+'/sim_zone_test.txt','w',newline='').write('\r\n'.join(t))
print('zone_monitor',len(mon),'| sim_zone_monitor',len(simmon),'| sim_zone_test',len(t))
