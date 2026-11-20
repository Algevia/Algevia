#!/usr/bin/env python3
"""Adds diagrams to bearings and circle-theorem questions that have none.
Usage: python3 add_diagrams.py bank.json bank_out.json"""
import re,json,sys
import math
W,H=340,230
HEAD=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Arial, Helvetica, sans-serif" font-size="15" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" role="img" aria-label="%s">'
def esc(s): return str(s).replace('&','&amp;').replace('<','&lt;').replace('"','&quot;')
def T(x,y,s,anchor='middle',size=15,bold=False):
    return f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="{size}" fill="currentColor" stroke="none"{" font-weight=\"bold\"" if bold else ""}>{esc(s)}</text>'
def L(a,b,dash=False,w=None): return f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}"'+(' stroke-dasharray="6 5"' if dash else '')+(f' stroke-width="{w}"' if w else '')+'/>'
def poly(pts,fill=None): return '<polygon points="'+' '.join(f'{x:.1f},{y:.1f}' for x,y in pts)+'"'+(f' fill="{fill}" fill-opacity="0.12"' if fill else '')+'/>'
def fit(pts,pad=48,w=W,h=H):
    xs=[p[0] for p in pts];ys=[p[1] for p in pts]
    sx=(w-2*pad)/max(1e-9,(max(xs)-min(xs)));sy=(h-2*pad)/max(1e-9,(max(ys)-min(ys)));s=min(sx,sy)
    ox=(w-s*(max(xs)-min(xs)))/2-s*min(xs);oy=(h-s*(max(ys)-min(ys)))/2+s*max(ys)
    return [(s*p[0]+ox,oy-s*p[1]) for p in pts]
def rightangle(P,A,B,size=12):
    ax,ay=A[0]-P[0],A[1]-P[1];bx,by=B[0]-P[0],B[1]-P[1]
    la=math.hypot(ax,ay);lb=math.hypot(bx,by);ax,ay,bx,by=ax/la*size,ay/la*size,bx/lb*size,by/lb*size
    return f'<polyline points="{P[0]+ax:.1f},{P[1]+ay:.1f} {P[0]+ax+bx:.1f},{P[1]+ay+by:.1f} {P[0]+bx:.1f},{P[1]+by:.1f}"/>'
def outward(P,Q,R,d=22):
    """point near vertex P pushed away from centroid of triangle PQR"""
    cx,cy=(P[0]+Q[0]+R[0])/3,(P[1]+Q[1]+R[1])/3;vx,vy=P[0]-cx,P[1]-cy;l=math.hypot(vx,vy)
    return (P[0]+vx/l*d,P[1]+vy/l*d)
def mid(a,b,off=0,ref=None):
    m=((a[0]+b[0])/2,(a[1]+b[1])/2)
    if off and ref:
        vx,vy=m[0]-ref[0],m[1]-ref[1];l=math.hypot(vx,vy) or 1;return (m[0]+vx/l*off,m[1]+vy/l*off+4)
    return m
def triangle(pts,vl=None,sides=None,angles=None,right=None,alt='Triangle',shade=True):
    """pts: 3 coords (math units, y up). vl: vertex labels. sides: {(i,j):text}. angles:{i:text} (label inside near vertex). right: index of right-angle vertex."""
    P=fit(pts);c=((P[0][0]+P[1][0]+P[2][0])/3,(P[0][1]+P[1][1]+P[2][1])/3)
    o=[HEAD%esc(alt),poly(P,'currentColor' if shade else None)]
    if right is not None:
        i=right;o.append(rightangle(P[i],P[(i+1)%3],P[(i+2)%3]))
    if vl:
        for i,lab in enumerate(vl):
            q=outward(P[i],P[(i+1)%3],P[(i+2)%3],20);o.append(T(q[0],q[1]+5,lab,bold=True))
    if sides:
        for (i,j),txt in sides.items():
            m=mid(P[i],P[j],24,c);o.append(T(m[0],m[1],txt))
    if angles:
        for i,txt in angles.items():
            a,b=P[(i+1)%3],P[(i+2)%3];v=P[i]
            ux,uy=a[0]-v[0],a[1]-v[1];wx,wy=b[0]-v[0],b[1]-v[1]
            lu,lw=math.hypot(ux,uy),math.hypot(wx,wy);bx,by=ux/lu+wx/lw,uy/lu+wy/lw;lb=math.hypot(bx,by)
            o.append(T(v[0]+bx/lb*34,v[1]+by/lb*34+5,txt))
    o.append('</svg>');return ''.join(o)
def sector(R_label,ang_label,theta=70,alt='Sector',shade=True):
    cx,cy,R=120,170,120;a=math.radians(theta)
    A=(cx+R,cy);B=(cx+R*math.cos(a),cy-R*math.sin(a))
    large=1 if theta>180 else 0
    d=f'M{cx},{cy} L{A[0]:.1f},{A[1]:.1f} A{R},{R} 0 {large} 0 {B[0]:.1f},{B[1]:.1f} Z'
    o=[HEAD%esc(alt),f'<path d="{d}"'+(' fill="currentColor" fill-opacity="0.12"' if shade else '')+'/>']
    o.append(T(cx+R/2+4,cy+22,R_label));
    bis=a/2;rr=R*0.58 if theta<60 else R*0.4;o.append(T(cx+rr*math.cos(bis),cy-rr*math.sin(bis)+5,ang_label,size=14))
    o.append(f'<circle cx="{cx}" cy="{cy}" r="2.5" fill="currentColor"/>');o.append('</svg>');return ''.join(o)
def circle_diagram(points,chords=(),centre=True,labels=True,tangent=None,alt='Circle',extra=(),R=88,notes=()):
    """points: dict name->angle deg (math, ccw from +x). chords: list of (name,name). tangent:(name,length) draws tangent at point. notes: [(x,y,text)] in px."""
    cx,cy=W/2,H/2+4
    P={k:(cx+R*math.cos(math.radians(v)),cy-R*math.sin(math.radians(v))) for k,v in points.items()}
    o=[HEAD%esc(alt),f'<circle cx="{cx}" cy="{cy}" r="{R}"/>']
    if centre:
        o.append(f'<circle cx="{cx}" cy="{cy}" r="2.5" fill="currentColor"/>');o.append(T(cx+10,cy-6,'O',bold=True))
    for a,b in chords:
        pa=P[a] if a in P else (cx,cy);pb=P[b] if b in P else (cx,cy);o.append(L(pa,pb))
    if tangent:
        nm,ln=tangent;ang=math.radians(points[nm]);tx,ty=-math.sin(ang),-math.cos(ang)
        p=P[nm];o.append(L((p[0]-tx*ln,p[1]-ty*ln),(p[0]+tx*ln,p[1]+ty*ln)))
    if labels:
        for k,v in P.items():
            ang=math.radians(points[k]);o.append(T(cx+(R+16)*math.cos(ang),cy-(R+16)*math.sin(ang)+5,k,bold=True))
    for x,y,txt in notes: o.append(T(x,y,txt,size=14))
    o.append('</svg>');return ''.join(o),P,(cx,cy)
def cuboid(l,w,h,alt='Cuboid',diag=None,labels=True):
    """oblique cuboid. returns svg. diag: list of (vertex,vertex) names to highlight dashed; vertices A..H."""
    x0,y0=60,190;sx,sy=170,110;dx,dy=70,-52
    # front face
    A=(x0,y0);B=(x0+sx,y0);C=(x0+sx,y0-sy);D=(x0,y0-sy)
    E=(A[0]+dx,A[1]+dy);F=(B[0]+dx,B[1]+dy);G=(C[0]+dx,C[1]+dy);Hh=(D[0]+dx,D[1]+dy)
    V=dict(A=A,B=B,C=C,D=D,E=E,F=F,G=G,H=Hh)
    o=[HEAD%esc(alt),poly([A,B,C,D]),poly([D,C,G,Hh]),poly([B,F,G,C]),L(A,E,True),L(E,F,True),L(E,Hh,True)]
    if diag:
        for a,b in diag: o.append(f'<line x1="{V[a][0]}" y1="{V[a][1]}" x2="{V[b][0]}" y2="{V[b][1]}" stroke-width="2.4" stroke-dasharray="7 4"/>')
    if labels:
        o+= [T((A[0]+B[0])/2,A[1]+20,f'{w} cm'),T(B[0]+dx/2+16,B[1]+dy/2+14,f'{l} cm'),T(A[0]-24,(A[1]+D[1])/2+5,f'{h} cm')]
        for k,v in V.items():
            off={'A':(-12,14),'B':(12,16),'C':(12,-6),'D':(-12,-6),'E':(-10,14),'F':(12,14),'G':(12,-6),'H':(-12,-8)}[k];o.append(T(v[0]+off[0],v[1]+off[1],k,bold=True))
    o.append('</svg>');return ''.join(o),V
def regular_polygon(n,alt='Regular polygon',mark='exterior'):
    cx,cy,R=W/2,H/2+4,82
    pts=[(cx+R*math.cos(math.radians(90+i*360/n)),cy-R*math.sin(math.radians(90+i*360/n))) for i in range(n)]
    o=[HEAD%esc(alt),poly(pts,'currentColor')]
    if mark=='exterior':
        a,b=pts[0],pts[1];vx,vy=b[0]-a[0],b[1]-a[1];l=math.hypot(vx,vy);ext=(b[0]+vx/l*40,b[1]+vy/l*40)
        o.append(L(b,ext));o.append(T(b[0]+vx/l*52,b[1]+vy/l*52-6,'x',size=15))
    o.append('</svg>');return ''.join(o)
def vec_triangle(pa,pb,alt='Triangle OAB with vectors',extra_pt=None,extra_label=None,la='a',lb='b'):
    O=(60,180);A=(280,180);B=(150,40)
    o=[HEAD%esc(alt),poly([O,A,B]),T(O[0]-14,O[1]+16,'O',bold=True),T(A[0]+14,A[1]+16,'A',bold=True),T(B[0],B[1]-10,'B',bold=True)]
    o.append(T((O[0]+A[0])/2,O[1]+22,la+' (OA)' if False else f'OA = {la}'));o.append(T((O[0]+B[0])/2-34,(O[1]+B[1])/2,f'OB = {lb}'))
    if extra_pt:
        t=extra_pt;M=(A[0]+(B[0]-A[0])*t,A[1]+(B[1]-A[1])*t);o.append(f'<circle cx="{M[0]:.1f}" cy="{M[1]:.1f}" r="3" fill="currentColor"/>');o.append(T(M[0]+16,M[1]-4,extra_label or 'M',bold=True))
    o.append('</svg>');return ''.join(o)

def parallel_lines(labels,alt='Two parallel lines cut by a transversal'):
    y1,y2=80,160;o=[HEAD%esc(alt),L((40,y1),(300,y1)),L((40,y2),(300,y2)),L((110,200),(230,40))]
    for y in (y1,y2): o.append(f'<polyline points="75,{y-6} 83,{y} 75,{y+6}"/>')
    xi=lambda y:110+(200-y)*0.75
    spots={'tl':(-8,-12,'end'),'tr':(24,-12,'start'),'bl':(-26,26,'end'),'br':(10,26,'start')}
    for k,v in labels.items():
        pos,line=k[:2],k[2:];y=y1 if line=='1' else y2;dx,dy,an=spots[pos]
        o.append(T(xi(y)+dx,y+dy,v,anchor=an,size=14))
    o.append('</svg>');return ''.join(o)

def boxplot(mn,lq,md,uq,mx,unit='',alt='Box plot'):
    lo=(mn//10)*10;hi=-(-mx//10)*10;x0,x1=36,W-30;sc=lambda v:x0+(v-lo)/(hi-lo)*(x1-x0);y=110
    o=[HEAD%esc(alt),L((x0,170),(x1,170))]
    for v in range(lo,hi+1,10): o.append(L((sc(v),165),(sc(v),175)));o.append(T(sc(v),192,str(v),size=13))
    o+= [L((sc(mn),y),(sc(lq),y)),L((sc(uq),y),(sc(mx),y)),f'<rect x="{sc(lq):.1f}" y="{y-28}" width="{sc(uq)-sc(lq):.1f}" height="56"/>',L((sc(md),y-28),(sc(md),y+28)),L((sc(mn),y-14),(sc(mn),y+14)),L((sc(mx),y-14),(sc(mx),y+14))]
    if unit: o.append(T(W/2,218,unit,size=13))
    o.append('</svg>');return ''.join(o)

def trapezium(a,b,h,alt='Trapezium'):
    la,lb=f'{a:g} cm',f'{b:g} cm'
    if a>b: a,b,la,lb=b,a,lb,la
    x0,x1,yb,yt=40,300,190,50
    w_b=x1-x0;w_t=w_b*a/b;off=(w_b-w_t)/2*0.55
    P=[(x0,yb),(x1,yb),(x0+off+w_t,yt),(x0+off,yt)]
    hx=x0+off+w_t*0.3
    o=[HEAD%esc(alt),poly(P,'currentColor'),T((P[2][0]+P[3][0])/2,yt-8,la),T((x0+x1)/2,yb+22,lb),
       L((hx,yt),(hx,yb),dash=True),rightangle((hx,yb),(hx+10,yb),(hx,yb-10),9),T(hx+6,(yt+yb)/2+5,h,anchor='start'),'</svg>']
    return ''.join(o)
def rectangle(l,w,alt='Rectangle'):
    x0,x1,y0,y1=50,290,50,180
    return ''.join([HEAD%esc(alt),poly([(x0,y0),(x1,y0),(x1,y1),(x0,y1)],'currentColor'),T((x0+x1)/2,y1+24,l),T(x1+8,(y0+y1)/2+5,w,anchor='start'),rightangle((x0,y1),(x0+10,y1),(x0,y1-10),9),'</svg>'])
def circle_radius(label,kind='radius',alt='Circle'):
    cx,cy,R=W/2,H/2,86
    o=[HEAD%esc(alt),f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="currentColor" fill-opacity="0.12"/>',f'<circle cx="{cx}" cy="{cy}" r="2.5" fill="currentColor"/>']
    if kind=='radius': o+= [L((cx,cy),(cx+R,cy)),T(cx+R/2,cy-8,label)]
    else: o+= [L((cx-R,cy),(cx+R,cy)),T(cx,cy-8,label)]
    o.append('</svg>');return ''.join(o)
def straight_line_angles(a_lab,x_lab,alt='Angles on a straight line'):
    y=150;o=[HEAD%esc(alt),L((30,y),(310,y)),L((150,y),(215,45))]
    o+= [T(105,y-14,a_lab,size=15),T(235,y-16,x_lab,size=15)]
    o.append('</svg>');return ''.join(o)

def ext_triangle(a_lab,b_lab,alt='Triangle ABC with BC extended to D'):
    A=(60,185);B=(255,185);C=(175,80);D=(C[0]+(C[0]-B[0])*0.5,C[1]+(C[1]-B[1])*0.5)
    o=[HEAD%esc(alt),poly([A,B,C],'currentColor'),L(C,D),T(A[0]-14,A[1]+6,'A',bold=True),T(B[0]+14,B[1]+6,'B',bold=True),T(C[0]+14,C[1]-4,'C',bold=True),T(D[0]-10,D[1]-4,'D',bold=True),
       T(A[0]+42,A[1]-8,a_lab),T(B[0]-44,B[1]-8,b_lab),T(C[0]-30,C[1]-6,'x'),'</svg>']
    return ''.join(o)

S=sys.modules[__name__]
def g(v):return f"{float(v):g}"
def dirv(b):
    t=math.radians(b);return (math.sin(t),math.cos(t))      # math coords, y up
def scene(pts,segs=(),norths=(),arcs=(),dots=True,alt='Bearing diagram',dashed=(),labels=(),right=None,order=None,compass=False):
    """pts name->(x,y) in math units. arcs: (pt,b1,b2,text). labels: (a,b,text)"""
    names=list(pts);P=S.fit([pts[n] for n in names],pad=58);P=dict(zip(names,P))
    cx=sum(p[0] for p in P.values())/len(P);cy=sum(p[1] for p in P.values())/len(P)
    o=[HEAD%esc(alt)]
    for a,b in segs:o.append(L(P[a],P[b]))
    if compass:
        best=max([(28,4),(W-28,4),(28,H-100),(W-28,H-100)],key=lambda c:min(math.hypot(c[0]-p[0],c[1]+40-p[1]) for p in P.values()));x0,y0=best
        o.append(f'<line x1="{x0}" y1="{y0+58}" x2="{x0}" y2="{y0+26}"/><polyline points="{x0-5},{y0+34} {x0},{y0+26} {x0+5},{y0+34}"/>'+T(x0,y0+76,'N',size=13,bold=True))
    for a,b in dashed:o.append(L(P[a],P[b],dash=True))
    for n in norths:
        p=P[n];o.append(L(p,(p[0],p[1]-44),dash=True));o.append(T(p[0],p[1]-50,'N',size=13,bold=True))
    for n,b1,b2,txt in arcs:
        p=P[n];r=24
        def pt(b,rr):d=dirv(b);return (p[0]+rr*d[0],p[1]-rr*d[1])
        a1,a2=pt(b1,r),pt(b2,r);span=(b2-b1)%360;large=1 if span>180 else 0
        o.append(f'<path d="M{a1[0]:.1f},{a1[1]:.1f} A{r},{r} 0 {large} 1 {a2[0]:.1f},{a2[1]:.1f}"/>')
        m=pt(b1+span/2,r+16);o.append(T(m[0],m[1]+4,txt,size=12))
    if right:
        a,b,c=right;o.append(S.rightangle(P[b],P[a],P[c]))
    for a,b,txt in labels:
        pa,pb=P[a],P[b];dx,dy=pb[0]-pa[0],pb[1]-pa[1];l=math.hypot(dx,dy) or 1
        nx,ny=-dy/l,dx/l
        if (pa[0]+pb[0])/2+nx<cx and len(P)>2 or (len(P)==2 and nx<0):nx,ny=-nx,-ny
        m=((pa[0]+pb[0])/2+nx*17,(pa[1]+pb[1])/2+ny*17+4);o.append(T(m[0],m[1],txt,size=13))
    for n,p in P.items():
        if dots:o.append(f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="3" fill="currentColor"/>')
        rays=[0.0]
        for x,y in list(segs)+list(dashed):
            if n in (x,y):
                q=P[y if x==n else x];rays.append(math.degrees(math.atan2(q[0]-p[0],-(q[1]-p[1])))%360)
        for an,b1,b2,txt in arcs:
            if an==n:rays.append((b1+((b2-b1)%360)/2)%360)
        best=max(range(0,360,10),key=lambda d:min(min(abs(d-r)%360,360-abs(d-r)%360) for r in rays))
        d=math.radians(best);o.append(T(p[0]+24*math.sin(d),p[1]-24*math.cos(d)+5,n,bold=True))
    o.append('</svg>');return ''.join(o)
def inside(P,c,k=30):
    vx,vy=c[0]-P[0],c[1]-P[1];l=math.hypot(vx,vy);return (P[0]+vx/l*k,P[1]+vy/l*k+4)
def addto(svg,extra):return svg.replace('</svg>',extra+'</svg>')
def circ(points,chords,notes_at,tangent=None,centre=True,alt='Circle',extra_fn=None):
    s,P,c=circle_diagram(points,chords=chords,centre=centre,tangent=tangent,alt=alt)
    ex=''.join(T(*inside(P[n],c,k),t,size=13) for n,t,k in notes_at)
    if extra_fn:ex+=extra_fn(P,c)
    return addto(s,ex)
def build(q):
    p=q['prompt'];t=q['topic']
    if t=='Bearings':
        m=re.match(r'The bearing of (\w) from (\w) is (\d+)°\.\nThe bearing of (\w) from \2 is (\d+)°\.\nWork out the size of angle',p)
        if m:
            X,A,b1,Y,b2=m.group(1),m.group(2),int(m.group(3)),m.group(4),int(m.group(5));d1,d2=dirv(b1),dirv(b2)
            return scene({A:(0,0),X:d1,Y:d2},segs=[(A,X),(A,Y)],norths=[A],arcs=[(A,0,b1,f'{b1:03d}°'),(A,0,b2,f'{b2:03d}°')],alt=f'Diagram: from {A}, {X} is on a bearing of {b1:03d} degrees and {Y} is on a bearing of {b2:03d} degrees, with a north line at {A}.')
        m=re.match(r'The bearing of (\w) from (\w) is (\d+)°\.(?:\n| )(?:Work out|Find) the bearing of \2 from \1',p)
        if m:
            X,A,b=m.group(1),m.group(2),int(m.group(3))
            return scene({A:(0,0),X:dirv(b)},segs=[(A,X)],norths=[A],arcs=[(A,0,b,f'{b:03d}°')],alt=f'Diagram: {X} is on a bearing of {b:03d} degrees from {A}, with a north line at {A}.')
        m=re.match(r'A boat sails (\d+) km north and then (\d+) km east\.\nWork out the (bearing|distance)',p)
        if m:
            a,b=int(m.group(1)),int(m.group(2))
            return scene({'Start':(0,0),'Turn':(0,a),'End':(b,a)},segs=[('Start','Turn'),('Turn','End')],dashed=[('Start','End')],compass=True,right=('Start','Turn','End'),labels=[('Start','Turn',f'{a} km'),('Turn','End',f'{b} km')],alt=f'Diagram: a boat sails {a} km north then {b} km east.')
        m=re.match(r'(?:A ship|A boat) sails (\d+) km on a bearing of (\d+)°\.',p)
        if m:
            d,b=int(m.group(1)),int(m.group(2))
            return scene({'Start':(0,0),'End':dirv(b)},segs=[('Start','End')],norths=['Start'],arcs=[('Start',0,b,f'{b:03d}°')],labels=[('Start','End',f'{d} km')],alt=f'Diagram: a ship sails {d} km on a bearing of {b:03d} degrees from its start, with a north line.')
        m=re.match(r'(\w) is (\d+) km from (\w) on a bearing of (\d+)°',p)
        if m:
            B,d,A,b=m.group(1),int(m.group(2)),m.group(3),int(m.group(4))
            return scene({A:(0,0),B:dirv(b)},segs=[(A,B)],norths=[A],arcs=[(A,0,b,f'{b:03d}°')],labels=[(A,B,f'{d} km')],alt=f'Diagram: {B} is {d} km from {A} on a bearing of {b:03d} degrees, with a north line at {A}.')
        m=re.match(r'A ship sails (\d+) km from P on a bearing of (\d+)° to Q\.\nIt then sails (\d+) km from Q on a bearing of (\d+)° to R',p)
        if m:
            d1,b1,d2,b2=int(m.group(1)),int(m.group(2)),int(m.group(3)),int(m.group(4))
            v1,v2=dirv(b1),dirv(b2);Q=(v1[0]*d1,v1[1]*d1);R=(Q[0]+v2[0]*d2,Q[1]+v2[1]*d2)
            return scene({'P':(0,0),'Q':Q,'R':R},segs=[('P','Q'),('Q','R')],dashed=[('P','R')],norths=['P','Q'],arcs=[('P',0,b1,f'{b1:03d}°'),('Q',0,b2,f'{b2:03d}°')],labels=[('P','Q',f'{d1} km'),('Q','R',f'{d2} km')],alt=f'Diagram: a ship sails {d1} km on a bearing of {b1:03d} degrees from P to Q, then {d2} km on a bearing of {b2:03d} degrees to R, with north lines at P and Q.')
        m=re.match(r'B is due ([a-z\-]+) of A\.',p)
        if m:
            D={'north':0,'north-east':45,'east':90,'south-east':135,'south':180,'south-west':225,'west':270,'north-west':315}
            if m.group(1) in D:
                b=D[m.group(1)]
                return scene({'A':(0,0),'B':dirv(b)},segs=[('A','B')],compass=True,alt=f'Diagram: B is due {m.group(1)} of A, with a north line at A.')
    if t=='Circle theorems':
        if p.startswith('ABCD is a cyclic quadrilateral'):
            m=re.search(r'Angle ABC = (\d+)° and angle ADC = (\d+)°',p)
            if m:
                return circ({'A':110,'B':200,'C':290,'D':20},[('A','B'),('B','C'),('C','D'),('D','A')],[('B',m.group(1)+'°',30),('D',m.group(2)+'°',30)],centre=False,alt='Cyclic quadrilateral ABCD with angle ABC and angle ADC marked.')
        if p.startswith('AB is a diameter'):
            m=re.search(r'Angle ACB = (\d+)°',p)
            if m:return circ({'A':180,'B':0,'C':65},[('A','B'),('A','C'),('C','B')],[('C',m.group(1)+'°',28)],centre=False,alt='Circle with diameter AB and a point C on the circle, angle ACB marked.')
        if p.startswith('A, B, C and D are points on a circle, with C and D'):
            m=re.search(r'Angle ACB = (\d+)° and angle ADB = (\d+)°',p)
            if m:return circ({'A':205,'B':335,'C':60,'D':120},[('A','B'),('A','C'),('C','B'),('A','D'),('D','B')],[('C',m.group(1)+'°',26),('D',m.group(2)+'°',26)],centre=False,alt='Circle with chord AB and points C and D on the same side of it, angles ACB and ADB marked.')
        if p.startswith('A, B and C are points on a circle. A tangent'):
            m=re.search(r'chord AB is (\d+)°',p)
            if m:
                a=m.group(1)
                def ex(P,c):
                    A=P['A'];return T(A[0]-34,A[1]+22,a+'°',size=13)+T(*inside(P['C'],c,26),a+'°',size=13)
                return circ({'A':90,'B':200,'C':330},[('A','B'),('C','A'),('C','B')],[],tangent=('A',80),centre=False,alt='Circle with a tangent at A, chord AB and a point C in the alternate segment, with the matching angles marked.',extra_fn=ex)
        if p.startswith('O is the centre of a circle. M is the point on chord AB'):
            def ex(P,c):
                A,B=P['A'],P['B'];M=((A[0]+B[0])/2,(A[1]+B[1])/2)
                return L(c,M)+T(M[0]+12,M[1]-6,'M',bold=True)+f'<circle cx="{M[0]:.1f}" cy="{M[1]:.1f}" r="2.5" fill="currentColor"/>'+S.rightangle(M,c,B,9)
            return circ({'A':205,'B':335},[('A','B')],[],centre=True,alt='Circle with centre O, chord AB and a line from O meeting AB at M at a right angle.',extra_fn=ex)
        if p.startswith('A, B and C are points on a circle with centre O'):
            m=re.search(r'Angle ACB = (\d+)° and angle AOB = (\d+)°',p)
            if m:return circ({'A':215,'B':325,'C':90},[('C','A'),('C','B'),('O','A'),('O','B')],[('C',m.group(1)+'°',26),('A',' ',0)] if False else [('C',m.group(1)+'°',26)],alt='Circle with centre O: angle ACB at the circumference and angle AOB at the centre stand on the same arc AB.',extra_fn=lambda P,c:T(c[0],c[1]+34,m.group(2)+'°',size=13))
        if p.startswith('O is the centre of a circle. PT is a tangent'):
            m=re.search(r'Angle OPT = (\d+)°',p)
            if m:
                def ex(P,c):
                    Pp=P['P'];return T(Pp[0]+30,Pp[1]-14,m.group(1)+'°',size=13)+T(Pp[0]+66,Pp[1]+18,'T',bold=True)
                return circ({'P':270},[('O','P')],[],tangent=('P',78),centre=True,alt='Circle with centre O, radius OP and a tangent PT at P.',extra_fn=ex)
        if p.startswith('O is the centre of a circle. A and B are points'):
            m=re.search(r'angle OAB = angle OBA = (\d+)°',p)
            if m:return circ({'A':215,'B':325},[('O','A'),('O','B'),('A','B')],[('A',m.group(1)+'°',34),('B',m.group(1)+'°',34)],alt='Circle with centre O and points A and B: triangle OAB has two equal radii OA and OB.')
    if t=='Circle Theorems Angles':
        m=re.match(r'A chord AB subtends an angle of (\d+)° at a point on the circumference',p)
        if m:return circ({'A':205,'B':335,'C':85},[('C','A'),('C','B'),('O','A'),('O','B')],[('C',m.group(1)+'°',26)],alt='Circle with centre O: chord AB subtends an angle at C on the circumference and an unknown angle at the centre.',extra_fn=lambda P,c:T(c[0],c[1]+34,'?',size=14))
    return None
def run(path,out=None):
    b=json.load(open(path));qs=b['questions'] if isinstance(b,dict) else b;n=0;fam={}
    for q in qs:
        if q.get('diagram_svg'):continue
        try:s=build(q)
        except Exception as e:print('ERR',q['id'],e);continue
        if s:
            alt=re.search(r'aria-label="([^"]*)"',s);q['diagram_svg']=s;q['diagram_alt']=alt.group(1) if alt else 'Diagram';n+=1;fam[q['topic']]=fam.get(q['topic'],0)+1
    json.dump(b,open(out or path,'w'),ensure_ascii=False);print(n,fam)
if __name__=='__main__':
    import sys;run(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else None)
