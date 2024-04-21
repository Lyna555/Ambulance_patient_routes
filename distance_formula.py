# Binomes: Boughaba Lina - Bousseboua Douaa

import numpy as np
import pandas as pd
from pyomo.environ import *
import itertools
import osmnx as ox
import networkx as nx
import folium as fm

# Graph osmnx
place_name = "constantine, Algeria"

G = ox.graph_from_place(place_name, network_type='drive')
fig, ax = ox.plot_graph(G)
G = ox.add_edge_speeds(G)
G = ox.add_edge_travel_times(G)

patient_count = 5
max_vehicle_count = 2

# Points: CHU + patients 
points = { 0:"CHU Constantine",  1:"université mentouri",
           2:"Beni Hamiden",  3:"Sidi Mabrouk",
           4:"Khroub"}

# Matrice des zeros
matrice = np.zeros(25)
temps_trajet = matrice.reshape(5,5)

# Remplir la matrice avec les temps du trajet entre patient i et patient j (inclus CHU)
for i in range(5):
    for j in range(5):
        if i != j :
            origin_coordinates=ox.geocode(points[i])
            destination_coordinates=ox.geocode(points[j])
            origin_node =ox.distance.nearest_nodes(G, origin_coordinates[1],origin_coordinates[0])
            destination_node =ox.distance.nearest_nodes(G, destination_coordinates[1],destination_coordinates[0])
            route = nx.shortest_path(G, origin_node, destination_node, weight='travel_time')
            temps_trajet[i,j] = round(sum(ox.utils_graph.get_route_edge_attributes(G, route, 'travel_time'))/60)

# Point du depart(CHU) sur folium
CHU_coordinates=ox.geocode(points[0])
m = fm.Map(location=[CHU_coordinates[0],CHU_coordinates[1]],zoom_start=12)

I = set(range(0,patient_count))

temps_service = [0, 30, 30, 50, 45]

# Densite

# mat = np.zeros(25)
# densite = mat.reshape(5,5)

# for i in I:
#     for j in I:
#         if i!=j:
#             densite[i,j] = round(((180-(temps_service[i]+temps_service[j]))*(180-(temps_service[i]+temps_service[j])))/temps_trajet[i,j])


for vehicle_count in range(1,max_vehicle_count+1):
    
    model = ConcreteModel()  

    model.patient = Set(initialize=range(patient_count))
    model.vehicles = Set(initialize=range(vehicle_count))
    
    model.x = Var(model.patient,model.patient,model.vehicles, within=Binary, doc="1 if taken route from i-th to j-th place taken by k-th vehicle, 0 otherwise")
    
    model.obj_total_cost = Objective(sense=minimize, expr=
            sum((temps_trajet[i,j] + temps_service[j]) * model.x[i, j, k]
                for i in range(patient_count)
                for j in range(patient_count) if j != i
                for k in range(vehicle_count)
            ), doc="Minimize total cost of routes taken by vehicles")
    
    model.c=ConstraintList()
 # Le patient doit etre visite par une seule ambulance
    for j in range( 1,patient_count):
        model.c.add(sum(model.x[i, j, k] if i != j else 0 for i in range(patient_count) for k in range(vehicle_count)) == 1)
  
 # l'ambulance doit sortir et rentrer du et vers le CHU
    for k in range(vehicle_count):
        model.c.add(sum(model.x[0, j, k] for j in range(1,patient_count)) == 1)
        model.c.add(sum(model.x[i, 0, k] for i in range(1,patient_count)) == 1)

 # la meme ambulance doit entrer et sortir du patient
    for k in range(vehicle_count):
        for j in range(patient_count):
             model.c.add(sum(model.x[i, j, k] if i != j else 0 for i in range(patient_count)) - sum(model.x[j, i, k] for i in range(patient_count)) == 0)

 # Le temps du trajet + le temps du service doit etre <= 7h
    for k in range(vehicle_count):
        model.c.add(sum((temps_trajet[i,j]+temps_service[i]) * model.x[i,j,k] if i!=j else 0 for i in range(patient_count) for j in range(patient_count)) <= 420)

 # Le temps du service doit etre <= 3h
    for k in range(vehicle_count):
        model.c.add(sum(temps_service[j] * model.x[i,j,k] if i!=j else 0  for i in range(patient_count) for j in range(patient_count)) <= 180)

 # Eliminer les sous-tournes
    subtours = []
    for i in range(2,patient_count):
         subtours += itertools.combinations(range(1,patient_count), i)

    for s in subtours:
         model.c.add(sum(model.x[i, j, k] if i !=j else 0 for i, j in itertools.permutations(s,2) for k in range(vehicle_count)) <= len(s) - 1)

SolverFactory('glpk').solve(model, tee=False)

List=list(model.x.keys())

for j in range(max_vehicle_count):
    print("L'ambulance",j+1,":")
    for i in List:
        if model.x[i]()==1 and j == i[2]:
            print("(",points[i[0]],",",points[i[1]],")")
    print()

# Creation des groupes d'ambulance  
features = []
for v in range(max_vehicle_count):
    name = 'Ambulance '+str(v+1)
    features.append(fm.FeatureGroup(name=name).add_to(m))

# Affichage sur osmnx
routes = []

colors = ['red', 'orange', 'yellow', 'green', 'purple']

for i in List:
    if model.x[i]()==1:
        origin_coordinates=ox.geocode(points[i[0]])
        destination_coordinates=ox.geocode(points[i[1]])
        origin_node =ox.distance.nearest_nodes(G, origin_coordinates[1],origin_coordinates[0])
        destination_node =ox.distance.nearest_nodes(G, destination_coordinates[1],destination_coordinates[0])
        routes.append(nx.shortest_path(G, origin_node, destination_node, weight='travel_time'))
        amb = 'Ambulance '+str(i[2]+1)
        fm.Marker((G.nodes[destination_node]['y'],G.nodes[destination_node]['x']), tooltip=(points[i[1]]), icon=fm.Icon(color=colors[i[2]])).add_to(features[i[2]])
        route_map = ox.plot_route_folium(G, nx.shortest_path(G, origin_node, destination_node, weight='travel_time'), route_map=features[i[2]], color=colors[i[2]],weight=6,opacity=0.8,tooltip=amb)

        
fig, ax = ox.plot_graph_routes(G, routes, route_color='r', route_linewidth=6, node_size=0)

# Affichage sur folium
fm.LayerControl().add_to(m)
route_map.save('route.html')