//dati grafici coefficienti correlazione pompa-turbina

clear()
clearglobal()
xdel(winsid())
clc

global handle_eta; //variabile per rendimento pompa selezionata da usare come HPRT
global QpBEP;
global HpBEP;
global Cq;
global Ch;
global etapBEP;
global eta;
global ro;
//global Qt_string;
//global Ht_string;
//global speed_string;
//global ro_string;
//global numST_string;
global Qt;
global Ht;
global speed;
global numST;
global ds;
global handle_QpBEPperc;
global QpBEPperc;
QpBEPperc=-1;
global QpBEPnew;
global g;
global handle_HpBEPnew;
global HpBEPnew;
global Qtrated;
global Htrated;
global Cqrated;
global Chrated;
global cont;
cont=0;
global NstSI;


//coeff portata
matrice_CQ=[
	0.770 0.840 0.930 1.025 1.125 1.240 1.370 1.520 1.650 1.780 1.870 1.950;
	0.730 0.790 0.870 0.980 1.075 1.175 1.295 1.445 1.550 1.700 1.800 1.900;
    0.680 0.740 0.825 0.930 1.030 1.120 1.230 1.370 1.480 1.620 1.750 1.850;
    0.650 0.700 0.780 0.890 0.985 1.070 1.160 1.300 1.400 1.550 1.685 1.800;
	0.630 0.675 0.755 0.850 0.950 1.025 1.105 1.240 1.340 1.480 1.630 1.755;
	0.605 0.650 0.730 0.810 0.917 0.990 1.060 1.180 1.280 1.425 1.580 1.710;
	0.580 0.625 0.705 0.785 0.880 0.950 1.010 1.140 1.235 1.375 1.535 1.670;
	0.563 0.607 0.680 0.750 0.850 0.910 0.975 1.097 1.190 1.330 1.495 1.630;
	0.545 0.590 0.660 0.730 0.827 0.880 0.940 1.060 1.150 1.300 1.460 1.600;
	0.530 0.570 0.643 0.712 0.870 0.850 0.907 1.027 1.110 1.270 1.420 1.570;
	0.523 0.560 0.627 0.700 0.780 0.825 0.882 1.000 1.080 1.235 1.390 1.540;
	0.518 0.550 0.610 0.690 0.760 0.802 0.868 0.970 1.050 1.207 1.367 1.510;
	0.505 0.540 0.600 0.677 0.745 0.782 0.850 0.950 1.030 1.180 1.340 1.480;
	0.500 0.530 0.590 0.670 0.735 0.770 0.838 0.930 1.010 1.152 1.320 1.460;
	0.495 0.525 0.580 0.660 0.720 0.760 0.825 0.920 1.000 1.135 1.300 1.440;
	0.490 0.525 0.575 0.652 0.715 0.755 0.815 0.905 0.992 1.120 1.280 1.430;
	0.490 0.522 0.570 0.646 0.708 0.747 0.807 0.900 0.990 1.110 1.270 1.420;
	0.495 0.520 0.570 0.650 0.700 0.740 0.800 0.890 0.980 1.100 1.260 1.410;
	0.497 0.525 0.570 0.648 0.700 0.740 0.800 0.890 0.980 1.100 1.250 1.400];

//coeff prevalenza

matrice_CH=[
    0.940 1.050 1.280 1.540 1.680 1.860 2.000 2.150 2.450 2.650;
    0.900 1.000 1.200 1.430 1.580 1.750 1.800 2.050 2.300 2.530;
    0.870 0.970 1.150 1.350 1.500 1.650 1.820 1.970 2.170 2.460;
    0.840 0.940 1.100 1.280 1.440 1.590 1.750 1.910 2.100 2.400;
	0.810 0.900 1.060 1.225 1.380 1.530 1.680 1.845 2.030 2.335;
	0.780 0.870 1.017 1.180 1.333 1.480 1.630 1.800 1.970 2.290;
	0.750 0.845 0.980 1.150 1.300 1.450 1.590 1.765 1.940 2.255;
	0.727 0.820 0.955 1.120 1.275 1.420 1.560 1.733 1.915 2.225;
	0.700 0.800 0.930 1.100 1.250 1.400 1.540 1.710 1.900 2.200;
	0.680 0.780 0.910 1.082 1.230 1.380 1.520 1.692 1.900 2.180;
	0.660 0.760 0.890 1.072 1.222 1.365 1.510 1.680 1.900 2.173;
	0.645 0.740 0.876 1.065 1.215 1.358 1.500 1.670 1.900 2.164;
	0.625 0.720 0.860 1.058 1.210 1.350 1.500 1.670 1.900 2.160;
	0.618 0.710 0.850 1.050 1.202 1.342 1.500 1.675 1.910 2.160;
	0.600 0.692 0.838 1.050 1.200 1.340 1.500 1.675 1.920 2.160;
	0.590 0.680 0.825 1.040 1.200 1.340 1.510 1.685 1.930 2.163;
	0.580 0.670 0.820 1.040 1.200 1.340 1.510 1.700 1.940 2.170;
	0.570 0.658 0.815 1.040 1.200 1.340 1.520 1.708 1.952 2.185;
	0.560 0.648 0.810 1.040 1.200 1.342 1.525 1.720 1.970 2.200];

//NS in unità anglosassoni - ascissa grafici
NS=[
	600.0 700.0 800.0 900.0 1000.0 1100.0 1200.0 1300.0 1400.0 1500.0 1600.0 1700.0 1800.0 1900.0 2000.0 2100.0 2200.0 2300.0 2400.0];

//% abbassamento rendimento pompa che opera come turbina - curve su grafico CQ-NS
eta=[
	0 19 36 49 64 72 80 88 93 96 95 92];

//coeff CQ - curve su grafico CH-NS
CQH=[
	0.6 0.8 1.0 1.2 1.3 1.4 1.5 1.6 1.7 1.8];


//Dati selezione turbina da richiesta cliente - trasformare in maschera con inserimento da tastiera
//Qt=76.79; //[m3/h]
//Ht=859; //[m]
//speed=2975; //[rpm]
//ro=.9864; //[kg/dm3]
//numST=10;
//ds=2; //1=single suction; 2=double suction

h=figure(0);
hinput=400;
linput=400;
h.position=[10 25 linput hinput]
toolbar(h.figure_id,'off')

val=[];
var=["Flowrate [m3/h]" "Qt";...
"Head [m]" "Ht";...
"Speed [rpm]" "speed";...
"Density [kg/dm^3]" "ro"; ...
"Stages [ ]" "numST"; ...
"Suction [1=single, 2=double]" "ds";...
];

pos_t_start=[5 (hinput-60)];

uicontrol(h, "style", "text", ...
"horizontalalignment", "center", ...
"string", "TURBINE DATA", ...
"position", [linput/2-230/2 hinput-30 230 20], ...
"fontsize",15);

x_edit_start=250;
[ninput, buttami]=size(var);
handle_edit=[];
z=0;
for z=1:ninput
    uicontrol(h, "style", "text", ...
             "string", var(z,1), ...
             "position", [pos_t_start(1) pos_t_start(2)-30*(z-1) 230 20], ...
             "fontsize",15);
    handle=uicontrol(h, "style", "edit", ...
             "string", "", ...
             "position", [x_edit_start pos_t_start(2)-30*(z-1) 100 20],...
             "BackgroundColor",[1 1 1]); 
     handle_edit=[handle_edit;handle];               
     pos_end=pos_t_start(2)-30*(z-1);
     //disp(handle_edit)
end 

h_calcola=uicontrol(h,"style","pushbutton",...
          "string", "Calculate", ...
          "position", [10 pos_end-40 100 20], ...
          "callback","leggodatiHPRT()");
          
h_load=uicontrol(h,"style","pushbutton",...
          "string", "Load data", ...
          "position", [120 pos_end-40 100 20], ...
          "callback","load_data()");


function leggodatiHPRT(val,ninput)
    global ro;
//    global Qt_string;
//    global Ht_string;
//    global speed_string;
//    global ro_string;
//    global numST_string;
    global Qt;
    global Ht;
    global speed;
    global numST;
    global ds;
    global NstSI;
    v=0;
    for v=1:ninput
        //disp(handle_edit)
        val=[val;handle_edit(v).string];
        //disp(val)
        execstr([var(v,2)+"="+val(v)]);
        //disp([var(v,2)+"="+val(v)])
    end
//    Qt_string=string(Qt);
//    Ht_string=string(Ht);
//    speed_string=string(speed);
//    ro_string=string(ro);
//    numST_string=string(numST);
    calcoloHPRT() //calcoloHPRT(Qt,Ht,speed,ro,numST,ds)
endfunction


function load_data(val,ninput)
    global ro;
//    global Qt_string;
//    global Ht_string;
//    global speed_string;
//    global ro_string;
//    global numST_string;
    global Qt;
    global Ht;
    global speed;
    global numST;
    global ds;
    path=uigetfile(["*.txt"],"C:\CFX\HPRT_AHPB19550\Turbine\Scilab"); 
    disp(["reading data from:";path])

    fd=mopen(path);
    txt=mgetl(fd);
    mclose(fd);
    for r=1:ninput
        //disp(handle_edit)
        val=[val;txt(r)];
        //disp(val)
        execstr([var(r,2)+"="+val(r)]);
        //disp([var(r,2)+"="+val(r)])
    end
//    Qt_string=string(Qt);
//    //disp(Qt_string)
//    Ht_string=string(Ht);
//    //disp(Ht_string)
//    speed_string=string(speed);
//    //disp(speed_string)
//    ro_string=string(ro);
//    //disp(ro_string)
//    numST_string=string(numST);
//    //disp(numST_string)
    calcoloHPRT() //calcoloHPRT(Qt,Ht,speed,ro,numST,ds)
endfunction


function mostrodatiPompa()
    global handle_eta;
    global QpBEP;
    global HpBEP;
    global Cq;
    global Ch;
    global handle_QpBEPperc;
    global g;
    global speed;
    global numST;
    global ds;
    
    g=figure(1);
    houtput=400;
    loutput=400;
    g.position=[linput+30 25 loutput houtput]
    toolbar(g.figure_id,'off')

    output=["Flowrate @ BEP: ",string(round(QpBEP*10)/10)," m3/h";...
    "Head @ BEP: ",string(round(HpBEP*10)/10)," m";...
    "Speed: ",string(speed)," rpm";...
    "Suction (1=single, 2=double): ",string(ds), " ";...
    "Stages: ", string(numST), " "];
    //disp(output)

    [noutput, buttami]=size(output);
 
    //disp(noutput)

    uicontrol(g, "style", "text", ...
    "horizontalalignment", "center", ...
    "string", "PUMP DATA", ...
    "position", [loutput/2-230/2 houtput-30 230 20], ...
    "fontsize",15);

    //output nella finestra pump data
    u=0;
    t=0;
    for u=1:noutput
        for t=1:2
            if t == 1 then
                uicontrol(g, "style", "text", ...
                "string", strcat(output(u,t)), ...
                "position", [pos_t_start(1) pos_t_start(2)-30*(u-1) 250 20], ...
                "BackgroundColor",[1 1 1],...
                "fontsize",15);
            else
                uicontrol(g, "style", "text", ...
                "string", strcat(output(u,2:3)), ...
                "position", [pos_t_start(1)+250*(t-1) pos_t_start(2)-30*(u-1) 250/t 20], ...
                "BackgroundColor",[1 1 1],...
                "fontsize",15);
            end
        end
    end

    //campi richiesta rendimento pompa selezionata
    uicontrol(g, "style", "text", ...
    "string", "Insert Efficiency @ BEP [%]:", ...
    "position", [pos_t_start(1) pos_t_start(2)-30*(noutput) 230 20], ...
    "BackgroundColor",[1 1 1],...
    "fontsize",15);
    handle_eta=uicontrol(g, "style", "edit", ...
    "string", "", ...
    "position", [x_edit_start pos_t_start(2)-30*(noutput) 100 20],...
    "BackgroundColor",[1 1 1]);
    //disp(QpBEP)
    uicontrol(g, "style", "text", ...
    "string", "Actual % of pump BEP:", ...
    "position", [pos_t_start(1) pos_t_start(2)-30*(noutput)-30 230 20], ...
    "BackgroundColor",[1 1 1],...
    "fontsize",15);
    handle_QpBEPperc=uicontrol(g, "style", "edit", ...
    "string", "", ...
    "position", [x_edit_start pos_t_start(2)-30*(noutput)-30 100 20],...
    "BackgroundColor",[1 1 1]);
    //disp(QpBEP)
        
    g_continue=uicontrol(g,"style","pushbutton",...
                "string", "Continue", ...
                "position", [120 pos_end-40-30 150 20], ...
                "callback",'richiestaetap()');
endfunction


function richiestaetap()
    global handle_eta;
    global etapBEP;
    global handle_QpBEPperc;
    global QpBEPperc;
    global g;
    global handle_HpBEPnew;
    //etapBEP=60;
    //disp(etapBEP)
    //disp(QpBEP)
    etapBEP=strtod(handle_eta.string);
    QpBEPperc=strtod(handle_QpBEPperc.string);
    if QpBEPperc==100 then
        plotPPC()
    else
        uicontrol(g, "style", "text", ...
        "string", "Actual pump BEP head [m]:", ...
        "position", [pos_t_start(1) pos_end-40-30*2 230 20], ...
        "BackgroundColor",[1 1 1],...
        "fontsize",15);
        handle_HpBEPnew=uicontrol(g, "style", "edit", ...
        "string", "", ...
        "position", [x_edit_start pos_end-40-30*2 100 20],...
        "BackgroundColor",[1 1 1]);

        g_ricalcola=uicontrol(g,"style","pushbutton",...
        "string", "Ricalculate", ...
        "position", [120 pos_end-40-30*3 150 20], ...
        "callback",'calcoloHPRT()');
    end
endfunction


function calcoloHPRT()
    global QpBEP;
    global HpBEP;
    global Cq;
    global Ch;
    global QpBEPperc;
    global QpBEPnew;
    global HpBEPnew;
    global ro;
    global Qt;
    global Ht;
    global speed;
    global numST;
    global ds;
    global Qtrated;
    global Htrated;
    global Cqrated;
    global Chrated;
    global cont;
    global runawayspeed;
    global NstSI;
    
    if cont==0
        Qtrated=Qt;
        Htrated=Ht;
        Cqrated=Cq;
        Chrated=Ch;
    end
    
    if QpBEPperc>0 then
        if QpBEPperc~=100 then
            if cont==0
                Qtrated=Qt;
                Htrated=Ht;
                Cqrated=Cq;
                Chrated=Ch;
            end
            QpBEPnew=QpBEP/(QpBEPperc/100)
            HpBEPnew=strtod(handle_HpBEPnew.string)
            Qt=QpBEPnew*Cq(10)
            Ht=HpBEPnew*Ch(10)
            cont=cont+1;
        end
    end
    
//    global ro;
//    global Qt_string;
//    global Ht_string;
//    global speed_string;
//    global ro_string;
//    global numST_string;
//    
//    Qt_string=string(Qt);
//    Ht_string=string(Ht);
//    speed_string=string(speed);
//    ro_string=string(ro);
//    numST_string=string(numST);
    
    
    //Calcolo Ns turbina
    if ds==2 then
        NstDOUBLE=speed*(Qt/3600/ds)^0.5/(Ht/numST)^0.75;
        NstSERIESST=speed*(Qt/3600)^0.5/(Ht/numST)^0.75;
        NstDS=NstDOUBLE*51.64;
        Nst=NstSERIESST*51.64;
        NstSI=(NstDOUBLE+NstSERIESST*(numST-1))/numST;
    elseif ds==1 then
        NstSI=speed*(Qt/3600)^0.5/(Ht/numST)^0.75;
        Nst=NstSI*51.64;
        NstDS=Nst;
    else
        disp("please state if HPRT is single suction or double suction");
    end
    
    //disp(NstSI);

    if Nst<600 then
        disp("ATTENTION: NS out of range, data interpolation maybe inconsistent!")
    elseif Nst>2400 then
        disp("ATTENTION: NS out of range, data interpolation maybe inconsistent!")
    elseif NstDS<600 then
        disp("ATTENTION: NS of double suction stage is out of range, data interpolation maybe inconsistent!")
    elseif NstDS>2400 then
        disp("ATTENTION: NS of double suction stage is out of range, data interpolation maybe inconsistent!")
    end

    k=1;
    for k=1:12
        vettore_Nst(k)=Nst;
        if ds==2 then
            vettore_NstDS(k)=NstDS;
        end
    end

    //Calcolo prestazioni pompa corrispondente ipotizzata al BEP
    i=1;
    for i=1:12
        d=splin(NS,matrice_CQ(:,i)');
        Cq(i)=interp(Nst,NS,matrice_CQ(:,i)',d);
        if ds==2 then
            CqDS(i)=interp(NstDS,NS,matrice_CQ(:,i)',d);
        end
    end
    d1=splin2d(NS,CQH,matrice_CH);
    Ch=interp2d(vettore_Nst,Cq,NS,CQH,d1);
    if ds==2 then
        ChDS=interp2d(vettore_NstDS,CqDS,NS,CQH,d1);
    end

    QpBEP=Qt/Cq(10);
    //disp(QpBEP)
    if ds==2 then
        QpBEPDS=Qt/CqDS(10);
        QpBEP=(QpBEPDS+QpBEP*(numST-1))/numST;
        Cq=(CqDS+Cq*(numST-1))/numST;
    end
    HpBEP=Ht/Ch(10)
    //disp(HpBEP)
    if ds==2 then
        HpBEPDS=Ht/ChDS(10);
        HpBEP=(HpBEPDS+HpBEP*(numST-1))/numST;
        Ch=(ChDS+Ch*(numST-1))/numST;
    end
    
    mostrodatiPompa()
endfunction

function plotPPC()
    global eta;
    global ro;
//    global Qt_string;
//    global Ht_string;
//    global speed_string;
//    global ro_string;
//    global numST_string;
    global Qt;
    global Ht;
    global speed;
    global numST;
    global ds;
    global Qtrated;
    global Htrated;
    global Cqrated;
    global Chrated;
    global NstSI;
    global runawayspeed;
    
    
    //mprintf('Please try to select a pump with the following performance @ BEP of max impeller diameter:\nFlow = %1.1f m3/h\nHead = %1.1f m\n', QpBEP, HpBEP)
    //PumpSelected=input("Have you found a pump selection between 90% and 110% of BEP @  Please insert rated point % respect to BEP of selected pump: ")

    //QpBEPperc=input("Please insert rated point % respect to BEP of selected pump: ")
    //QpBEPperc=100;
    //
    //if QpBEPperc~=100 then //da sviluppare per pompa selezionata non al BEP
    //    QpBEP=input("Please insert actual BEP flow of selected pump [m3/h]: ")
    //    HpBEP=input("Please insert actual BEP head of selected pump [m]: ")
    //end

    //etapBEP=input("Please insert efficiency @ BEP of selected pump [%]: ")
    //etapBEP=55;

    //Disegno PPC HPRT
    npunti=5; //variare il numero di punti su cui interpolare tra 5 e 10 se il problema è mal condizionato
    npunti_fine=4000;
    qHPRT=QpBEP*Cq';
    disp(qHPRT)
    qqHPRT=linspace(qHPRT(1),qHPRT($),npunti);
    qqqHPRT=linspace(qHPRT(1),qHPRT($),npunti_fine);
    hHPRT=HpBEP*Ch'
    if Cq(12) > 1.8 then
        hHPRT(12)=hHPRT(12)*1.04; //usare se CQ > 1.8 per l'ultimo punto di portata, regolare coeff fino a 1.1 per allungare fondocurva
    end
    
    disp(hHPRT)
    //dd=splin(qHPRT,hHPRT);
    //hhHPRT=interp(qqHPRT,qHPRT,hHPRT,dd);
    [hhHPRT,dd]=lsq_splin(qHPRT,hHPRT,qqHPRT);
    ddd=splin(qqHPRT,hhHPRT);
    hhhHPRT=interp(qqqHPRT,qqHPRT,hhHPRT,ddd);
    hHPRTrated=interp(Qtrated,qqHPRT,hhHPRT,ddd);
    etaHPRT=etapBEP/100*eta;
    disp(etaHPRT)
    //dd1=splin(qHPRT,etaHPRT);
    //etaetaHPRT=interp(qqHPRT,qHPRT,etaHPRT,dd1);






    [etaetaHPRT,dd1]=lsq_splin(qHPRT,etaHPRT,qqHPRT);
    //disp(etaetaHPRT)
    ddd1=splin(qqHPRT,etaetaHPRT);
    etaetaetaHPRT=interp(qqqHPRT,qqHPRT,etaetaHPRT,ddd1);
    etaHPRTrated=interp(Qtrated,qqHPRT,etaetaHPRT,ddd1);

    pHPRT=ro*9.80665/3600/100*qHPRT.*hHPRT.*etaHPRT;
    //disp(ro)
    //disp(pHPRT)
    ppHPRT=ro*9.80665/3600/100*qqHPRT.*hhHPRT.*etaetaHPRT; //calcolo potenza in uscita dalla turbina [kW]
    //disp(ppHPRT)
    pppHPRT=ro*9.80665/3600/100*qqqHPRT.*hhhHPRT.*etaetaetaHPRT;
    pHPRTrated=ro*9.80665/3600/100*Qtrated*Htrated*etaHPRTrated;

    screen_size=get(0,"screensize_pt");
    hPPC=screen_size(4)*1.15;
    //disp(hPPC)
    lPPC=screen_size(3);
    //disp(lPPC)
    PPC=figure(2);
    PPC.toolbar_visible="off";
    //PPC.menubar_visible="off";
    PPC.figure_position=[lPPC*.167 hPPC*.167/3];
    PPC.figure_size=[lPPC hPPC];
    PPC.background=-2;
    
    //Creazione frame performance
    PPC_frame=uicontrol(PPC,"relief","groove",...
                    "style","frame",...
                    "position",[lPPC-250 hPPC/4 230 hPPC*2/3],...
                    "horizontalalignment","center","background",[1 1 1]); 
    PPC_frame_title=uicontrol(PPC,"style","text",...
                        "string","PERFORMANCE CURVES DATA",...
                        "position",[lPPC-250+25 hPPC/4+hPPC*2/3-10 230-50 20],...
                        "fontsize",12,"horizontalalignment","center",...
                        "background",[ 1 1 1]);
    
    //plot tabella riassuntiva prestazioni HPRT
    params=["Fluid:" "Flow:" "Head:" "Efficiency:" "Power:" "Speed:" "Density:" "Dyn. viscosity:" "Kin. viscosity:" "Temperature:" "Stages:"]';
    //disp(params)
    //values=[" " Qt_string Ht_string string(etaHPRT(10)) string(round(pHPRT(10)*10)/10) speed_string ro_string " " " " " " numST_string]';
    //disp(values)
    values=[" " string(round(Qt*100)/100) string(round(Ht*100)/100) string(etaHPRT(10)) string(round(pHPRT(10)*10)/10) string(speed) string(ro) " " " " " " string(numST)]';
    //disp(values)
    units=[" " "[m^3/h]" "[m]" "[%]" "[kW]" "[rpm]" "[kg/dm^3]" "[cP]" "[cSt]" "[°C]" " "]';
    
    for s=1:size(params,1)
        uicontrol(PPC,"relief","groove","style","text",...
            "string",params(s),...
            "position",[lPPC-250+10 hPPC/4+hPPC*2/3-50-30*(s-1) 210 30],...
            "horizontalalignment","left",...
            "fontsize",12,...
            "background",[.95 .95 .95]);
    end
    
    s=0;
    for s=1:size(values,1)
        if s==1 then
            uicontrol(PPC,"relief","flat","style","edit",...
            "string",values(s),...
            "position",[lPPC-250+10+80 hPPC/4+hPPC*2/3-50-30*(s-1)+2.5 125 25],...
            "horizontalalignment","left",...
            "verticalalignment","middle",...
            "fontsize",12,...
            "background",[.95 .95 .95]);
        else
            uicontrol(PPC,"relief","flat","style","edit",...
            "string",values(s),...
            "position",[lPPC-250+10+80 hPPC/4+hPPC*2/3-50-30*(s-1)+2.5 50 25],...
            "horizontalalignment","left",...
            "verticalalignment","middle",...
            "fontsize",12,...
            "background",[.95 .95 .95]);
        end
    end
    
    s=0;
    for s=1:size(units,1)
        if s>1 then
            uicontrol(PPC,"relief","flat","style","text",...
            "string",units(s),...
            "position",[lPPC-250+10+130 hPPC/4+hPPC*2/3-50-30*(s-1)+2.5 50 25],...
            "horizontalalignment","left",...
            "verticalalignment","middle",...
            "fontsize",11,...
            "background",[.95 .95 .95]);
        end
    end
    
//    //Plot prestazioni @ rated point //da usare se rated point non al BEP
//    PPC_frame_title2=uicontrol(PPC,"style","text",...
//                        "string","PERFORMANCE @ RATED POINT",...
//                        "position",[lPPC-250+25 hPPC/4+hPPC*2/3-50-30*s+2.5 230-50 20],...
//                        "fontsize",12,"horizontalalignment","center",...
//                        "background",[ 1 1 1]);
//    s=0;
//    for s=2:5
//        uicontrol(PPC,"relief","groove","style","text",...
//            "string",params(s),...
//            "position",[lPPC-250+10 hPPC/4+hPPC*2/3-50-30*size(units,1)+2.5-30*(s-1) 210 30],...
//            "horizontalalignment","left",...
//            "fontsize",12,...
//            "background",[.95 .95 .95]);
//    end
//    
//    s=0;
//    for s=1:4
//        if s==1 then
//            uicontrol(PPC,"relief","flat","style","edit",...
//            "string",string(Qtrated),...
//            "position",[lPPC-250+10+80 hPPC/4+hPPC*2/3-50-30*size(units,1)+5.5-30*s 50 25],...
//            "horizontalalignment","left",...
//            "verticalalignment","middle",...
//            "fontsize",12,...
//            "background",[.95 .95 .95]);
//        elseif s==2
//            uicontrol(PPC,"relief","flat","style","edit",...
//            "string",string(round(hHPRTrated*10)/10),...
//            "position",[lPPC-250+10+80 hPPC/4+hPPC*2/3-50-30*size(units,1)+5.5-30*s 50 25],...
//            "horizontalalignment","left",...
//            "verticalalignment","middle",...
//            "fontsize",12,...
//            "background",[.95 .95 .95]);
//        elseif s==3
//            uicontrol(PPC,"relief","flat","style","edit",...
//            "string",string(round(etaHPRTrated*10)/10),...
//            "position",[lPPC-250+10+80 hPPC/4+hPPC*2/3-50-30*size(units,1)+5.5-30*s 50 25],...
//            "horizontalalignment","left",...
//            "verticalalignment","middle",...
//            "fontsize",12,...
//            "background",[.95 .95 .95]);
//        elseif s==4
//            uicontrol(PPC,"relief","flat","style","edit",...
//            "string",string(round(pHPRTrated*10)/10),...
//            "position",[lPPC-250+10+80 hPPC/4+hPPC*2/3-50-30*size(units,1)+5.5-30*s 50 25],...
//            "horizontalalignment","left",...
//            "verticalalignment","middle",...
//            "fontsize",12,...
//            "background",[.95 .95 .95]);
//        end
//    end
//    
//    s=0;
//    for s=2:5
//        uicontrol(PPC,"relief","flat","style","text",...
//        "string",units(s),...
//        "position",[lPPC-250+10+130 hPPC/4+hPPC*2/3-50-30*size(units,1)+5.5-30*(s-1) 50 25],...
//        "horizontalalignment","left",...
//        "verticalalignment","middle",...
//        "fontsize",11,...
//        "background",[.95 .95 .95]);
//    end

    //Creazione frame dati cliente
    PPC_frame=uicontrol(PPC,"relief","groove",...
                    "style","frame",...
                    "position",[20 5 lPPC-40 hPPC*1/6],...
                    "horizontalalignment","center","background",[1 1 1]); 
    
    //plot tabella riassuntiva dati cliente
    dati1=["" "HPRT type: " "Curve n°: "];
    //disp(dati1)
    dati2=["Cust: " "Impeller diameter: 0 [mm]" "Impeller pattern: "];
    //disp(dati2)
    dati3=["Item: " "Impeller mat.: " "Casing mat.: " "Selection n°: "];
    //disp(dati3)
    
    s=0;
    for s=1:size(dati1,2)
        if s==1 then
            uicontrol(PPC,"relief","flat","style","image",...
            "string","LogoPS_piccolo.jpg",...//"string","logocolori_piccolo.png",...
            "position",[25+(lPPC-40-10)/3*(s-1) 10+(hPPC*1/6-10)*2/3 (lPPC-40-10)/3 (hPPC*1/6-10)/3],...
            "horizontalalignment","left",...
            "verticalalignment","middle",...
            "fontsize",16,...
            "background",[1 1 1]);
        else
            uicontrol(PPC,"relief","flat","style","edit",...
            "string",dati1(s),...
            "position",[25+(lPPC-40-10)/3*(s-1) 10+(hPPC*1/6-10)*2/3 (lPPC-40-10)/3 (hPPC*1/6-10)/3],...
            "horizontalalignment","left",...
            "verticalalignment","middle",...
            "fontsize",16,...
            "background",[.95 .95 .95]);
        end
    end
    
    s=0;
    for s=1:size(dati2,2)
        uicontrol(PPC,"relief","flat","style","edit",...
        "string",dati2(s),...
        "position",[25+(lPPC-40-10)/3*(s-1) 10+(hPPC*1/6-10)*1/3 (lPPC-40-10)/3 (hPPC*1/6-10)/3],...
        "horizontalalignment","left",...
        "verticalalignment","middle",...
        "fontsize",16,...
        "background",[.95 .95 .95]);
    end
    
    s=0;
    for s=1:size(dati3,2)
        uicontrol(PPC,"relief","flat","style","edit",...
        "string",dati3(s),...
        "position",[25+(lPPC-40-10)/4*(s-1) 10 (lPPC-40-10)/4 (hPPC*1/6-10)/3],...
        "horizontalalignment","left",...
        "verticalalignment","middle",...
        "fontsize",16,...
        "background",[.95 .95 .95]);
    end

    
//    table=[params values units]
//    as=PPC.axes_size
//    uicontrol(PPC,"style","table",..
//    "string",table,..
//    "horizontalalignment", "left", ...
//    "position",[as(1)-150 0 150 hPPC*2/3]);
    
    
    // Creo i frames dove mettere i grafici
    //c=createConstraints("gridbag", [0 hPPC lPPC-230 hPPC*5/6], [1,1], "both");
    top=uicontrol(PPC, "style", "frame",...
            "position", [0 hPPC-(hPPC*5/6-20)/3-40 lPPC-250 (hPPC*5/6-20)/3]);//"constraints", c);
    middle=uicontrol(PPC, "style", "frame",...
            "position", [0 hPPC-(hPPC*5/6-20)/3*2-27.5 lPPC-250 (hPPC*5/6-20)/3]);//"constraints", c);
    bottom=uicontrol(PPC, "style", "frame",...
            "position", [0 hPPC-(hPPC*5/6-20)/3*3-15 lPPC-250 (hPPC*5/6-20)/3]);//"constraints", c);

//    c.grid = [0 0 0 0];
//    middle = uicontrol(f, "style", "frame", "constraints", c);
//
//    c.grid = [0 0 0 0];
//    bottom = uicontrol(f, "style", "frame", "constraints", c);
    
    a_t=newaxes(top);
    a_m=newaxes(middle);
    a_b=newaxes(bottom);
    
//    subplot(4,1,3);
//    plot(qqHPRT,etaetaHPRT,'r');
//    plot(a_b,qHPRT,etaHPRT,'*b'); //commentare per curva cliente
    plot(a_b,qqqHPRT,etaetaetaHPRT,'k');
    plot(a_b,Qtrated,etaHPRTrated,'*r');
    xgrid;
    xlabel("Flow [m^3/h]", "fontsize", 2);
    ylabel("Efficiency [%]", "fontsize", 2, "color", "black");
//    subplot(4,1,2);
//    plot(qqHPRT,ppHPRT,'r');
//    plot(a_m,qHPRT,pHPRT,'*b'); //commentare per curva cliente
    plot(a_m,qqqHPRT,pppHPRT,'k');
    plot(a_m,Qtrated,pHPRTrated,'*r');
    xgrid;
    ylabel("Power [kW]", "fontsize", 2, "color", "black");
//    subplot(4,1,1);
//    plot(qqHPRT,hhHPRT,'r');
//    plot(a_t,qHPRT,hHPRT,'*b'); //commentare per curva cliente
    plot(a_t,qqqHPRT,hhhHPRT,'k');
    plot(a_t,Qtrated,hHPRTrated,'*r');
//    //punti operativi aggiuntivi
//    plot(a_t,2554,538,'*b');
//    xstringb(2554,538*1.05,"Max",20,20)
//    plot(a_t,2241,457,'*b');
//    xstringb(2241,457*1.05,"Min",20,20)
    xgrid;
    ylabel("Head [m]", "fontsize", 2, "color", "black");
    
    //saveGui(PPC, "HPRT_performance_curve.xml");
    
    //exportUI(2)
    
    //h = gcf();
    //h.axes_size =[640 480];
    //xs2bmp(h,'prova.bmp');
    //xs2ps(h, 'PPC_HPRT.ps', 'landscape')
    //xs2svg(h, 'PPC_HPRT.svg')
    
    //printfigure(2);
    
    
    //calcolo velocità di fuga della turbina (servono Qt per Pt=0 kW, NSt)
    runawayspeed=NstSI*(Htrated/numST)^0.75/(qHPRT(1)/3600)^0.5;
    disp("rpm",string(round(runawayspeed/10)*10),"The runaway speed of turbine is")
    
endfunction

