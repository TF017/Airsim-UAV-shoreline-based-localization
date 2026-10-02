import numpy as np
import pickle
import os
import matplotlib.pyplot as plt
import pandas as pd

PATH=r'Pickle_data'
files=[file for file in os.listdir(PATH) if file.endswith('v16_final.pkl')]
all_info=[]
for file in files:
    x=open(os.path.join(PATH, file), 'rb')
    info=pickle.load(x)
    all_info= all_info + info  #arrays.append([np.load(), file])
    x.close()

rows=[]
last=[None, None, None, None, None, None];i=0;
for diag, gt, place, ned, altitude, pitch, offshore, mode in all_info: #distance, pitch, altitude, place
    if type(diag)==type(None):
        continue
    q,w=diag['position'][0]-gt[0],diag['position'][1]-gt[1]
    e=np.sqrt(q**2 + w**2)
    current=[place, ned, altitude, pitch, offshore, mode]
    if last==current:
        i+=1;
    else:
        i=0;
    last=current

    rows.append({
                "place": place,
                "altitude": float(int(altitude)),
                "path_index": i,
                "error": e,
                "system": ned,
                "pitch": pitch,
                "offshore": offshore,
                'n_total_matches': diag['n_total_matches'],
                'n_inliers': diag['n_inliers'],
                'median_reproj_error': diag['median_reproj_error'],
                'rmse_reproj_error': diag['rmse_reproj_error'],            
                'inlier_spread': diag['inlier_spread'],
                'inlier_indices': diag['inlier_indices'],
            })

df = pd.DataFrame(rows)
global_df=df
#df=df[(df["offshore"]==0)]
#df=df[(df["pitch"]==-50) & (df["offshore"]==0)]
#df=df[(df["place"]=="Zambujeira") & (df["pitch"]==-50) & (df["offshore"]==0) & (df["altitude"]==150)]#(df["offshoere"]==0)
#df=df[(df["offshore"]==0) & (df["altitude"]==150) & (df['system']==False) & (df["pitch"]!=-78)] #(df["offshoere"]==0)
print(df[df['path_index']==0])
print(f"There are {len(df)} entries with respect to {len(df[df['path_index']==0])} different control paths")
import seaborn as sns
import matplotlib.pyplot as plt


#OFFSHORE 
df=global_df[(global_df["offshore"]!=0)]
fig, axes = plt.subplots(1, 2, figsize=(6,3.6))
#axes=[axes]
sns.boxplot(
    data=df,
    x="offshore",
    y="error",
    hue="place",
    showfliers=False,
    ax=axes[0]
)
axes[0].set_ylim(0, 1000)
axes[0].set_xlabel("Offshore distance [m]")
axes[0].set_ylabel("Error [m]")

sns.boxplot(
    data=df,
    x="offshore",
    y="n_total_matches",
    hue="place",
    showfliers=True,
    ax=axes[1]
)
axes[1].set_xlabel("Offshore distance [m]")
axes[1].set_ylabel("# Matches")

plt.rcParams.update({
    "font.size": 12,
    "axes.labelsize": 12,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "legend.fontsize": 10,
})
plt.legend()
plt.tight_layout()
plt.savefig(f'lightglue_offshore_error_place.pdf')
plt.show() 


#Altitude
df=global_df[(global_df["pitch"]==-50) & (global_df["offshore"]==0)]
fig, axes = plt.subplots(1, 2, figsize=(6,3.6))
#axes=[axes]
sns.boxplot(
    data=df[(df["altitude"]<=100)],
    x="altitude",
    y="error",
    hue="place",
    showfliers=True,
    ax=axes[0]
)
#axes[0].set_ylim(0, 1000)
axes[0].set_xlabel("Relative Altitude [m]")
axes[0].set_ylabel("Error [m]")

sns.boxplot(
    data=df[(df["altitude"]>=100)],
    x="altitude",
    y="error",
    hue="place",
    showfliers=True,
    ax=axes[1]
)
axes[1].set_ylim(0, 40)
axes[1].set_xlabel("Relative Altitude [m]")
axes[1].set_ylabel("Error [m]")

plt.rcParams.update({
    "font.size": 12,
    "axes.labelsize": 12,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "legend.fontsize": 10,
})
plt.legend()
plt.tight_layout()
plt.savefig(f'lightglue_altitude_sweep.pdf')
plt.show() 


#Altitude - Inliers
df=global_df[(global_df["pitch"]==-50) & (global_df["offshore"]==0)]
fig, axes = plt.subplots(1, 2, figsize=(6,3.6))
#axes=[axes]
sns.boxplot(
    data=df,
    x="altitude",
    y="n_total_matches",
    hue="place",
    showfliers=True,
    ax=axes[0]
)
axes[0].set_xlabel("Relative Altitude [m]")
axes[0].set_ylabel("# Matches")


sns.boxplot(
    data=df,
    x="altitude",
    y="n_inliers",
    hue="place",
    showfliers=True,
    ax=axes[1]
)
axes[1].set_xlabel("Relative Altitude [m]")
axes[1].set_ylabel("# Inliers")
 
plt.rcParams.update({
    "font.size": 12,
    "axes.labelsize": 12,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "legend.fontsize": 10,
})
plt.legend()
plt.tight_layout()
plt.savefig(f'lightglue_altitude_sweep_matches.pdf')
plt.show() 


#Pitch - Error
df=global_df[(global_df["offshore"]==0)]
fig, axes = plt.subplots(1, 2, figsize=(6,3.6))
#axes=[axes]
sns.boxplot(
    data=df[(df["altitude"]==150)],
    x="pitch",
    y="error",
    hue="place",
    showfliers=True,
    ax=axes[0]
)
axes[0].set_ylim(0, 300)
axes[0].set_xlabel("Camera Pitch [°]")
axes[0].set_ylabel("Error [m]")

sns.boxplot(
    data=df[(df["altitude"]==300)],
    x="pitch",
    y="error",
    hue="place",
    showfliers=True,
    ax=axes[1]
)
axes[1].set_ylim(0, 20)
axes[1].set_xlabel("Camera Pitch [°]")
axes[1].set_ylabel("Error [m]")

plt.rcParams.update({
    "font.size": 12,
    "axes.labelsize": 12,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "legend.fontsize": 10,
})
plt.legend()
plt.tight_layout()
plt.savefig(f'lightglue_pitch_sweep.pdf')
plt.show()  

#Pitch - Error
df=global_df[(global_df["offshore"]==0)]
df=df[(df["altitude"]==300) | (df["altitude"]==300)]
fig, axes = plt.subplots(1, 2, figsize=(6,3.6))
#axes=[axes]
sns.boxplot(
    data=df,
    x="pitch",
    y="n_total_matches",
    hue="place",
    showfliers=True,
    ax=axes[0]
)
#axes[0].set_ylim(0, 300)
axes[0].set_xlabel("Camera Pitch [°]")
axes[0].set_ylabel("# Matches")

sns.boxplot(
    data=df,
    x="pitch",
    y="n_inliers",
    hue="place",
    showfliers=True,
    ax=axes[1]
)
#axes[1].set_ylim(0, 20)
axes[1].set_xlabel("Camera Pitch [°]")
axes[1].set_ylabel("# Inliers")

plt.rcParams.update({
    "font.size": 12,
    "axes.labelsize": 12,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "legend.fontsize": 10,
})
plt.legend()
plt.tight_layout()
plt.savefig(f'lightglue_pitch_sweep_matches.pdf')
plt.show() 

