import os
import pandas
import json
import sys

PATH=r'D:\Thesis_Data'
##place, system, altitude, pitch, route, route generator, offshore, mask?, imu?, barometer?, error??, comments
library=[]
paths=[path for path in os.listdir(PATH) if path.isnumeric()]
paths=sorted(paths, key=lambda x: int(x))
for path in paths:
    full_path_place=os.path.join(PATH, path)
    with open(os.path.join(full_path_place, 'info.json'), 'r') as file:
        info=json.load(file)
        info['Camera Yaw']=info['Camera Angles'][0]
        info['Camera Pitch']=info['Camera Angles'][1]
        info['Camera Roll']=info['Camera Angles'][2]
        info['Path']=full_path_place
        del info['Camera Angles']
        del info['Obs']
        library.append(info)
    if info['Masked']==False and os.path.exists(os.path.join(full_path_place, 'masks')):
        with open(os.path.join(full_path_place, 'info.json'), 'r') as file:
            old_info=json.load(file)
        with open(os.path.join(full_path_place, 'info.json'), 'w') as file:
            old_info['Masked']=True
            json.dump(old_info, file)
library=pandas.DataFrame(library)           

#print(library)
def get_Orto_path(place):
    path=os.path.join(PATH, place)
    return os.path.join(path, 'orto_with_mask.tif')

def get_Place_info(place):
    if place=='Aveiro':
        return [-8.749156, 40.633197, 5.0]
    elif place=='Zambujeira':
        return [-8.810189, 37.612989, 49.0]
    elif place=='Lagoa de Albufeira':
        return [-9.181394, 38.517997, 18.0]
    else:
        raise BaseException('UNKNOW PLACE:', place)

def get_row_info(row):
    if type(row)==pandas.core.frame.DataFrame:
        row=row.iloc[0]
    if type(row)==pandas.core.series.Series:
        place=row['Place']
        return (place, row['System']=='NED', row['Altitude'],
                [row['Camera Yaw'],row['Camera Pitch'],row['Camera Roll']],
                  row['Offshore'], row['Path'],
                get_Place_info(place), get_Orto_path(place))
    #Must be an array or numpy array
    place=row[0]
    if type(place)==type(''):
        return (place, row[1]=='NED', row[2], [row[7], row[8], row[9]],
                 row[3], row[10] , get_Place_info(place), get_Orto_path(place)) 
    else:
        return get_row_info(place) #place is actually a row in this case

def get_row(place=None, system=None, altitude=None, pitch=None,
             offshore=None, masked=None, route=None, route_controller=None):
    q=library
    if place:
        q=q[q['Place']==place]
    if system:
        q=q[q['System']==system]
    if altitude:
        q=q[(q['Altitude']>=altitude[0]) & (q['Altitude']<=altitude[1])]
    if pitch:
        q=q[(q['Camera Pitch']>=pitch[0]) & (q['Camera Pitch']<=pitch[1])]
    if offshore:
        q=q[(q['Offshore']>=offshore[0]) & (q['Offshore']<=offshore[1])]
    if masked!=None:
        q=q[q['Masked']==masked]
    if route:
        q=q[q['Route']==route]
    if route_controller:
        q=q[q['Route Controller']==route_controller]
    return q

if __name__=='__main__':
    args=sys.argv
    n_args=len(args)-1
    place=None
    system=None
    altitude=None
    pitch=None
    offshore=None
    masked=None
    route=None
    route_controller=None
    if n_args:
        for arg in args[1:]:
            if 'place=' in arg:
                place=arg.replace('place=', '')
            elif 'system=' in arg:
                system=arg.replace('system=', '')
            elif 'masked=' in arg:
                masked=arg.replace('masked=', '')=='True'
            elif 'route=' in arg:
                route=arg.replace('route=', '')
            elif 'routeController=' in arg:
                route_controller=int(arg.replace('routeController=', ''))
            elif 'altitude=' in arg:
                altitude=arg.replace('altitude=', '')
                if '[' in altitude:
                    lower=float(altitude[1:altitude.find(', ')])
                    higher=float(altitude[altitude.find(', ')+2:-1])
                    altitude=[lower, higher]
                else:
                    altitude=[float(altitude), float(altitude)]
            elif 'pitch=' in arg:
                pitch=arg.replace('pitch=', '')
                if '[' in pitch:
                    lower=float(pitch[1:pitch.find(', ')])
                    higher=float(pitch[pitch.find(', ')+2:-1])
                    pitch=[lower, higher]
                else:
                    pitch=[float(pitch), float(pitch)]
            elif 'offshore=' in arg:
                offshore=arg.replace('offshore=', '')
                if '[' in offshore:
                    lower=float(offshore[1:offshore.find(', ')])
                    higher=float(offshore[offshore.find(', ')+2:-1])
                    offshore=[lower, higher]
                else:
                    offshore=[float(offshore), float(offshore)]
    q=get_row(place=place, system=system, altitude=altitude, pitch=pitch,
             offshore=offshore, masked=masked, route=route, route_controller=route_controller)        
    print(q)