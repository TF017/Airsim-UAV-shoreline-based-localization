import numpy as np
import pickle
import os
import matplotlib.pyplot as plt
import pandas as pd

PATH=r'Pickle_data'
files=[file for file in os.listdir(PATH) if file.endswith('_v15.pkl') and 'shore' in file]
all_info=[]
for file in files:
    x=open(os.path.join(PATH, file), 'rb')
    info=pickle.load(x)
    all_info= all_info + info  #arrays.append([np.load(), file])
    x.close()

rows=[]
last=None;i=0;
for diag, gt, distance, pitch, altitude, place in all_info: 
    if type(diag)==type(None):
        continue
    q,w=diag['position'][0]-gt[0],diag['position'][1]-gt[1]
    e=np.sqrt(q**2 + w**2)
    if last==altitude:
        i+=1;
    else:
        i=0;
    last=altitude
    rows.append({
                "place": place,
                "distance": distance,
                "path_index": i,
                "error": e,
            })

df = pd.DataFrame(rows)
#df=df[df['place']!='Lagoa de Albufeira']

import seaborn as sns
import matplotlib.pyplot as plt

# g = sns.relplot(
#     data=df,
#     x="path_index",
#     y="error",
#     hue="altitude",
#     col="place",
#     kind="line",
#     height=5,
#     aspect=1.5
# )

# g=sns.scatterplot(
#     data=df,
#     x="path_index",
#     y="error",
#     hue="altitude",
#     style="place",
#     s=40
# )


# Example structure
# place | altitude | path_index | error
'''
g = sns.relplot(
    data=df,
    x="path_index",
    y="error",
    hue="altitude",
    col="place",
    kind="scatter",
    palette="viridis_r",     # darkens with value
    alpha=0.7,
    s=40,
    height=5,
    aspect=1.4
)

g.set_axis_labels("Valid PnP Solution Number", "Error")
g.set_titles("Location: {col_name}")
g.set(ylim=(0, 1000))
plt.show()
#g.set_axis_labels("Path Position", "Error")
#g.set_titles("Place: {col_name}")
#
'''

# pivot = df[(df["place"] == "Zambujeira") & (df['error']<1000)].pivot(
#     index="altitude",
#     columns="path_index",
#     values="error"
# )

#g=sns.heatmap(pivot)
#g.set(lim=(0,1000))
#plt.show()

#plt.show()

""" sns.boxplot(
    data=df,
    x="altitude",
    y="error",
    hue="place"
)
plt.show() """


""" plt.figure(figsize=(10,6))

sns.boxplot(
    data=df,
    x="altitude",
    y="error",
    hue="place"
)

plt.xlabel("Altitude")
plt.ylabel("Error")
plt.title("Error Distribution vs Altitude")

plt.show()  """

""" sns.violinplot(
    data=df,
    x="altitude",
    y="error",
    hue="place",
    split=True
)

plt.show() """

""" sns.scatterplot(
    data=df,
    x="altitude",
    y="error",
    hue="place",
    alpha=0.3
)

sns.regplot(
    data=df,
    x="altitude",
    y="error",
    scatter=False,
    color="black"
)

plt.show() """

""" sns.lineplot(
    data=df,
    x="altitude",
    y="error",
    hue="place",
    errorbar="sd"
)

plt.show() """

""" fig, axes = plt.subplots(1, 2, figsize=(14,6))

# Full range
sns.boxplot(
    data=df,
    x="altitude",
    y="error",
    hue="place",
    ax=axes[0]
)

axes[0].set_title("Full Error Range in meters")

# Zoomed range
sns.boxplot(
    data=df,
    x="altitude",
    y="error",
    hue="place",
    ax=axes[1]
)

axes[1].set_ylim(0, 50)   # adjust zoom
axes[1].set_title("Zoomed Low-Error Region")

plt.tight_layout()
plt.show() """

""" plt.figure(figsize=(10,6))

s=sns.boxplot(
    data=df,
    x="distance",
    y="error"
)

s.set_ylim(0,250)
plt.xlabel("Camera Pitch Angle (deg)")
plt.ylabel("Error")
plt.title("Effect of Camera Pitch on Error [m] at 300m altitude")

plt.show() """

fig, axes = plt.subplots(1, 2, figsize=(14,6))

# Full range
sns.boxplot(
    data=df,
    x="distance",
    y="error",
    hue="place",
    ax=axes[0]
)

axes[0].set_title("Full Error Range in meters")

# Zoomed range
sns.boxplot(
    data=df,
    x="distance",
    y="error",
    hue="place",
    ax=axes[1]
)

axes[1].set_ylim(0, 50)   # adjust zoom
axes[1].set_title("Zoomed Low-Error Region")

plt.tight_layout()
plt.show()