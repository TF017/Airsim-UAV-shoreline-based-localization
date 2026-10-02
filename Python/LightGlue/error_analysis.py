import numpy as np
import matplotlib.pyplot as plt
import os

PATH=r'.'
files=[file for file in os.listdir(PATH) if file.endswith('.npy')]
arrays=[]
for file in files:
    arrays.append([np.load(os.path.join(PATH, file)), file])

print(f'Adding {arrays[0][1]}')
error=arrays[0][0]
for i in range(1, len(arrays)):
    print(f'Adding {arrays[i][1]}')
    error=np.concatenate((error, arrays[i][0]))

'''
L=len(error)
mask = (
    #(error[:, 6]/error[:, 7] >= 50) & #Matches >= 50
    (error[:, 6] >= 50)   #Inliners >=50 (best one)
    #(error[:, 2] < 50.0) #Height Error < 50 (seems  irrelevant)
    )
error = error[mask]
print(len(error), f"It is {len(error)/L*100:.2f} % of the original.")
'''
ransac_error=[]
ransac_error_no_z=[]
extrinsic_error=[]
extrinsic_error_no_z=[]

#[RANSAC ERRORX3; Extrinsic Errorx3; Inliners; Percentage of Inliners; U RMSE; V RMSE;]
for r_x, r_y, r_z, e_x, e_y, e_z, n_in, p_in, u_rmse, v_rmse in error:
#for r_x, r_y, r_z, n_in, p_in, u_rmse, v_rmse in error:
    ransac_error.append(np.linalg.norm([r_x, r_y, r_z]))
    ransac_error_no_z.append(np.linalg.norm([r_x, r_y]))
    extrinsic_error.append(np.linalg.norm([e_x, e_y, e_z]))
    extrinsic_error_no_z.append(np.linalg.norm([e_x, e_y]))
    

ransac_error=np.array(ransac_error)
ransac_error_no_z=np.array(ransac_error_no_z)
extrinsic_error=np.array(extrinsic_error)
extrinsic_error_no_z=np.array(extrinsic_error_no_z)
r_x_rmse=np.sqrt(np.mean(error[:, 0]**2))
r_y_rmse=np.sqrt(np.mean(error[:, 1]**2))
r_z_rmse=np.sqrt(np.mean(error[:, 2]**2))
e_x_rmse=np.sqrt(np.mean(error[:, 3]**2))
e_y_rmse=np.sqrt(np.mean(error[:, 4]**2))
e_z_rmse=np.sqrt(np.mean(error[:, 5]**2))

print(round(r_x_rmse, 2), round(r_y_rmse, 2), round(r_z_rmse, 2), round(np.sqrt(np.mean(ransac_error**2)),2), round(np.sqrt(np.mean(ransac_error_no_z**2)), 2))
print(round(e_x_rmse, 2), round(e_y_rmse, 2), round(e_z_rmse, 2), round(np.sqrt(np.mean(extrinsic_error**2)),2), round(np.sqrt(np.mean(extrinsic_error_no_z**2)), 2))
x=[error[:, 6], error[:, 7], (error[:, 6]/error[:, 7]), error[:, 8], error[:, 9], error[:, 2], error[:, 5]]
variables_names="ransac_error, ransac_error_no_z, extrinsic_error, extrinsic_error_no_z, n_in, p_in, points, u_rmse, v_rmse, ransac_altitude_error, extrinsic_altitude_error".split(', ')
variables=[ransac_error, ransac_error_no_z, extrinsic_error, extrinsic_error_no_z, error[:, 6], error[:, 7], error[:, 6]/error[:, 7], error[:, 8], error[:, 9], error[:, 2], error[:, 5]]
for i in range(len(x)):
    j=i+4
    print(f'{variables_names[j]}:\n\tMean: {x[i].mean():.2f}\tStd: {x[i].std():.2f}\tMax: {x[i].max():.2f}\tMin: {x[i].min():.2f}')


#variables=[ransac_error, ransac_error_no_z, error[:, 3], error[:, 4], error[:, 5], error[:, 6]]
#variables_names="ransac_error, ransac_error_no_z, n_in, p_in, u_rmse, v_rmse".split(', ')
for i in [0]:#range(0, len(variables)):
    for j in range(i+1, len(variables)):
        print(variables_names[i], variables_names[j], np.corrcoef(variables[i], variables[j])[0, 1])



fig, ax = plt.subplots()

scatter = ax.scatter(range(len(ransac_error_no_z)), ransac_error_no_z, s=error[:, 6], c=error[:, 7])
#scatter = ax.scatter(range(len(ransac_error_no_z)), ransac_error_no_z, s=error[:, 3], c=error[:, 4])

# produce a legend with the unique colors from the scatter
legend1 = ax.legend(*scatter.legend_elements(),
                    loc="upper left", title="Perc. of Inliners")
ax.add_artist(legend1)

# produce a legend with a cross-section of sizes from the scatter
handles, labels = scatter.legend_elements(prop="sizes", alpha=0.6)
legend2 = ax.legend(handles, labels, loc="upper right", title="# Inliners")

#ax.set(ylim=(0, 50))

plt.show()