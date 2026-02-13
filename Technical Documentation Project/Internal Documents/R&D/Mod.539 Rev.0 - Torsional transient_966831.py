""" The code can be used for "transient torsional analyses" to evaluate shaft
stresses during transients. It creates a Goodman diagram for the selected
element and verifies with Palmgren-Miner rule the component life.

Refer to ASTM E1049-85 for the standard practice of cycle counting method. The
code utilizes the rainflow method.

At the beginning of the code there are some inputs to define manually. In a 
first section there are the material properties, such as tensile strength and 
yield strength, and other input parameters required for the fatigue analysis,
such as shaft diameter, working temperature, surface type finiture and a 
reliable value of endurance limit. In a second section, there are:
-	inputfile : 	the filename of stresses during transient condition
-	kfile : 		the filename of fatigue stress concentration factor
-	fileout : 		the output filename
-	shaft_name : 	the shaft name of which the fatigue analysis has been 
					performed. It is the shaft name inside the inputfile
-	alfa_limit :	the limit for fatigue failure. Default value is 1.
-	graph : 		the shaft element for which the script will create a Goodman 
					diagram
For more information refer to "SOP.557 Level 3 Transient forced response 
analysis".

Attention! Import rainflow module from https://pypi.org/project/rainflow/
"""
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
# Material
Su = 660.           # ultimate tensile stress [MPa]
Sy = 520.           # yield stress [MPa]
diameter = 140.     # shaft diameter [mm]
temp = 107.          # temperature [°C]
surf = 2            # 1 = mirror polished;
                    # 2 = fine ground or commercially polished
                    # 3 = machined or cold drawn
                    # 4 = hot-rolled
                    # 5 = as forged
reliab = 4          # 1 = 50%
                    # 2 = 90%
                    # 3 = 99%
                    # 4 = 99.9%
#------------------------------------------------------------------------------
# Input
inputfile = "TRA_87009_torsional_transient_startup_rev001.txt"
kfile = "k_factor.txt"
fileout = "results.txt"
shaft_name = "Shaft 87009"
alfa_limit = 1.     # limit for Miner's rule
graph = 55          # element for which create graph
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
import math as mt
import numpy as np
import rainflow
from matplotlib import pyplot
import matplotlib.pyplot as plt
#------------------------------------------------------------------------------
# gradient factor Cg
if diameter < 10.:      Cg = 1.
elif diameter < 50.:    Cg = 0.9
elif diameter < 100.:   Cg = 0.8
else:                   Cg = 0.7
#------------------------------------------------------------------------------
# surface factor Cs
matrix_Cs = [[60.,80.,100.,120.,140.,155.,160.,180.,200.,220.,240.,260.]]
matrix_Cs.append([1.00,1.00,1.00,1.00,1.00,1.00,1.00,1.00,1.00,1.00,1.00,1.00])
matrix_Cs.append([0.90,0.90,0.90,0.90,0.90,0.90,0.89,0.86,0.83,0.80,0.76,0.71])
matrix_Cs.append([0.80,0.78,0.76,0.73,0.71,0.69,0.68,0.65,0.63,0.59,0.56,0.51])
matrix_Cs.append([0.74,0.64,0.58,0.52,0.47,0.44,0.43,0.39,0.35,0.31,0.28,0.24])
matrix_Cs.append([0.57,0.47,0.41,0.37,0.33,0.30,0.30,0.27,0.24,0.21,0.17,0.14])
Cs = np.interp(Su/6.894757, matrix_Cs[0], matrix_Cs[surf])
#------------------------------------------------------------------------------
# temperature factor Ct
f = (temp * 1.8) + 32
if f <= 840.:   Ct = 1.
else:           Ct = 1-(0.0032*f-2.688)
#------------------------------------------------------------------------------
# reliability factor Cr
matrix_Cr = [1.,0.897,0.868,0.814,0.753]
Cr = matrix_Cr[reliab]
#------------------------------------------------------------------------------
# load factor (torsional) Cl
Cl = 0.58
#------------------------------------------------------------------------------
# S-N curve
Sf = 0.9*Ct*0.8*Su                  # 1000 cycles
Sn = Cl*Cg*Cs*Ct*Cr*0.5*Su          # 1000000 cycles
a = Sf**2/Sn
b = -1/3*mt.log10(Sf/Sn)
N = lambda tau:(tau/a)**(1/b)       # cycles in function of S
#------------------------------------------------------------------------------
# concentration factor
inputk = open(kfile, "r")           # open file with concentration factors
linea = inputk.readline()
k_factor = []
while 1:
    linea = inputk.readline()
    if not linea: break    
    ele,kl,kr = linea.split(",")
    k_factor.append([float(kl),float(kr)])
inputk.close()
#------------------------------------------------------------------------------
# open result file
inputTTR = open(inputfile, "r")
position = []
results = []
time = []
#------------------------------------------------------------------------------
# identify positions in the file for each element of shaft
while 1:
    linea = inputTTR.readline()
    if not linea: break
    elif linea[0:len(shaft_name)] == shaft_name: position.append(inputTTR.tell())
n_ele = len(position)
#------------------------------------------------------------------------------
# count number of time step
inputTTR.seek(position[0])      # rewind file
while 1:
    linea = inputTTR.readline()
    if linea[0] != " ": break
    temp1,temp2= linea.split()
    time.append(float(temp1))
    linea = inputTTR.readline()
n_time = len(time)
#------------------------------------------------------------------------------
# read results for each elements
output = open(fileout,"w")
output.write("EleID    Side  alfa        Message\n")
for i in range(n_ele):
    inputTTR.seek(position[i])                # rewind file
    tau_left = []
    tau_right = []
    meanL = []
    altL = []
    meanR = []
    altR = []
    for j in range(n_time):
        temp1,temp2= inputTTR.readline().split()
        tau_left.append(k_factor[i][0]*1E-6*float(temp2))
        temp3,temp4= inputTTR.readline().split()
        tau_right.append(k_factor[i][1]*1E-6*float(temp3))
    alfa = 0.
    check = "ok"
    for rng, mean, count, i_start, i_end in rainflow.extract_cycles(tau_left):
        meanL.append(abs(mean))
        altL.append(abs(rng/2))
        if mean <= 0.8* Su:
            Saeq = 0.8*Su/(0.8*Su-mean)*rng/2
            if Saeq > Sf: check = "not ok: Saeq > Sf"
            elif Saeq >= Sn: alfa = alfa + count/N(Saeq)
        else: check = "not ok: Sm > Sus"
        if alfa > alfa_limit: check = "not ok: alfa > alfa_limit"
    output.write("%-8d left  %-12f%s\n" %(i+1,alfa,check))
    alfa = 0.
    check = "ok"
    for rng, mean, count, i_start, i_end in rainflow.extract_cycles(tau_right):
        meanR.append(abs(mean))
        altR.append(abs(rng/2))
        if mean <= 0.8* Su:
            Saeq = 0.8*Su/(0.8*Su-mean)*rng/2
            if Saeq > Sf: check = "not ok: Saeq > Sf"
            elif Saeq >= Sn: alfa = alfa + count/N(Saeq)
        else: check = "not ok: Sm > Sus"
        if alfa > alfa_limit: check = "not ok: alfa > alfa_limit"
    output.write("%-8d right %-12f%s\n" %(i+1,alfa,check)) 
    if i == graph:
        plt.subplot(1, 2, 1)
        plt.plot(time, tau_left, label = "left")
        plt.plot(time, tau_right, label = "right")
        plt.grid(True)
        plt.xlabel('time [s]')
        plt.ylabel(r'$\tau$'+' [MPa]')
        plt.legend()
        plt.subplot(1, 2, 2)
        plt.plot([0.,0.8*Su], [Sf,0.],color = 'k',linestyle = '--',linewidth = 1)
        plt.plot([0.,0.8*Su], [Sn,0.],color = 'k',linestyle = '--',linewidth = 1)
        plt.plot([0.,0.58*Sy], [0.58*Sy,0.],color = 'r',linestyle = '--',linewidth = 1)
        plt.plot(meanL, altL,linewidth = 0, marker = 'o')
        plt.plot(meanR, altR,linewidth = 0, marker = 'o')
        plt.grid(True)
        plt.xlim(0, Su)
        plt.ylim(0, Su)
        plt.xlabel(r'$\tau$'+'$_m$'+' [MPa]')
        plt.ylabel(r'$\tau$'+'$_a$'+' [MPa]')
        plt.fill_between([0.,0.8*Su],[Sn,0.],[Sf,0.],facecolor='gold',alpha=0.2)
        plt.fill_between([0.,0.8*Su],[Sn,0.],facecolor='green',alpha=0.2)
        plt.show()
inputTTR.close()
output.close()    