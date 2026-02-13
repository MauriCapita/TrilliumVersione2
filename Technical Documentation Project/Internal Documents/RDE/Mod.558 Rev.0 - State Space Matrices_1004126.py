"""
The allows to create the matrices A, B and C for the state space system 
starting from Nastran results HDF5 files. 
The script uses python modules tables.py to read and manipulate data within 
the output file and numpy.py to store and manage data in matrices.

It requires as input parameters:
-   filename:       the name of Nastran modal analysis results. The file 
                    should be in the same folder of this script
-   nodi:           the identification number of shaft nodes at bearing (and 
                    wear ring) locations in the structural model
-   DOF:            the lateral degree of freedom in the coordinate system of 
                    modal analysis. Use characters 'X', 'Y' or 'Z'. In 
                    horzontal pumps insert first the vertical axis and then 
                    the horizontal axis
-   damping_ratio:  the modal damping of structural system. Default is 1%

For more information refer to "SOP.585 - Level 3 - Pump rotordymancis adressed 
as a combined rotor and structural analysis - VS pump
"""
#----DATI INPUT---------------------------------------------------------------
filename = '20294_modale_wet_rev02.h5'
nodi = [102291,102286,102287,102288,102292,102293]
DOF = ('Y','X')
damping_ratio = 0.01
#-----------------------------------------------------------------------------
import tables
import numpy as np
#-----------------------------------------------------------------------------
# open file
h5=tables.open_file(filename)
#-----------------------------------------------------------------------------
# Lettura autovalori e autovettori
eigenvalue = h5.root.NASTRAN.RESULT.SUMMARY.EIGENVALUE
eigenvector = h5.root.NASTRAN.RESULT.NODAL.EIGENVECTOR
n_modi = eigenvalue.nrows
n_nodi = (eigenvector.nrows)//n_modi
#-----------------------------------------------------------------------------
# Matrice omega quadro
omega = eigenvalue.read()
omega2 = np.diag(-omega['EIGEN'])
#-----------------------------------------------------------------------------
# Matrice zeta
zeta = 2*damping_ratio*np.diag(-omega['OMEGA'])
#-----------------------------------------------------------------------------
# Matrice phi
phi=np.zeros(n_modi)
for index_nodi in nodi:
    for index_DOF in DOF:
        phi0 = eigenvector.read_where('ID == index_nodi',field=index_DOF)
        phi = np.vstack((phi,phi0))
phi=np.delete(phi,0,0)
#-----------------------------------------------------------------------------
A = np.vstack((np.hstack((np.zeros((n_modi,n_modi)),np.identity(n_modi))),np.hstack((omega2,zeta))))
#-----------------------------------------------------------------------------
B = np.vstack((np.zeros(np.transpose(phi).shape),np.transpose(phi)))
#-----------------------------------------------------------------------------
C = np.hstack((phi,np.zeros(phi.shape)))
#-----------------------------------------------------------------------------
outA = open('A.txt', "w")
np.savetxt(outA,A,fmt='%.6e')
outB = open('B.txt', "w")
np.savetxt(outB,B,fmt='%.6e')
outC = open('C.txt', "w")
np.savetxt(outC,C,fmt='%.6e')
#-----------------------------------------------------------------------------
# close file
h5.close()
outA.close()
outB.close()
outC.close()