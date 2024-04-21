import numpy as np
import osmnx as ox
import networkx as nx
import folium as fm

place_name = "constantine, Algeria"

G = ox.graph_from_place(place_name, network_type='drive')
fig, ax = ox.plot_graph(G)
G = ox.add_edge_speeds(G)
G = ox.add_edge_travel_times(G)

patient_count = 6
vehicules = 2

# Points: CHU + patients 
points = { 0:"CHU Constantine", 1:"université mentouri",
           2:"Beni Hamiden", 3:"Sidi Mabrouk",
           4:"Khroub", 5:"Ibn Badis"}

# Matrice des zeros
matrice = np.zeros(36)
temps_trajet = matrice.reshape(6,6)

# Remplir la matrice avec les temps du trajet entre patient i et patient j (inclus CHU)
for i in range(6):
    for j in range(6):
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
temps_service = [0, 60, 60, 50, 45, 30]

# Calcule de densite
mat = np.zeros(36)
densite = mat.reshape(6,6)

for i in I:
    for j in I:
        if i!=j:
            densite[i,j] = round(((180-(temps_service[i]+temps_service[j]))**2)/temps_trajet[i,j])

# Fonction objectif
def evaluate(sol, densite):
    c = 0
    for i in range(len(sol)-2):
        c = c + densite[sol[i] , sol[i+1]]
    
    c = c + densite[sol[len(sol)-1] , sol[0]]
    return c

# Creation de la tourne geante
def geantTour() :
    
    tab = []
    k = 0
    
    for i in range(6):
       m = float('inf')
       for j in range(6):
           if k!=j and tab.count(j)==0 and densite[k,j]<m:
               m = densite[k,j]
       if m != float('inf'):
           k = np.where(densite[k] == m)[0][0]
           tab.append(k)
              
    return tab

#Main
sol = geantTour()
sol.remove(0)
score = evaluate(sol, densite)

print('Solution: ')
print('- Visited patients:',sol)
print('- Total densite: ',score)
print()

trajet_count = 0
service_count = 0
vehicule = {}

for i in range(1,vehicules+1):
    vehicule.update({i:[0]})

vehicule_count = 1

sol.insert(0,0)

for i in range(len(sol)):
    if trajet_count >= 420 or service_count >= 180 and vehicule_count < vehicules:
        
        trajet_count = 0
        service_count = 0
        
        index = len(vehicule[vehicule_count])-1
        sol.insert(index,0)
        
        vehicule[vehicule_count].append(0)
        vehicule_count += 1
        # vehicule.update({vehicule_count:[0]})
                    
    trajet_count += temps_trajet[sol[i],sol[i+1]]
    trajet_count += temps_trajet[sol[i+1],0]
    service_count += temps_service[sol[i+1]]
                
    if trajet_count < 420 and service_count < 180:
        trajet_count -= temps_trajet[sol[i+1],0]
        vehicule[vehicule_count].append(sol[i+1])

vehicule[vehicule_count].append(0)
                
for i in vehicule:
    print('Vehicule',i,'tour:',vehicule[i])

# Creation des groupes d'ambulance  
features = []
for v in range(vehicule_count):
    name = 'Ambulance ' + str(v+1)
    features.append(fm.FeatureGroup(name=name).add_to(m))

# Affichage sur osmnx
routes = []

colors = ['red', 'orange', 'yellow', 'green', 'purple']

for i in vehicule:
    for j in range(len(vehicule[i])-1):
        origin_coordinates=ox.geocode(points[vehicule[i][j]])
        destination_coordinates=ox.geocode(points[vehicule[i][j+1]])
        origin_node =ox.distance.nearest_nodes(G, origin_coordinates[1],origin_coordinates[0])
        destination_node =ox.distance.nearest_nodes(G, destination_coordinates[1],destination_coordinates[0])
        routes.append(nx.shortest_path(G, origin_node, destination_node, weight='travel_time'))
        amb = 'Ambulance '+str(i)
        fm.Marker((G.nodes[destination_node]['y'],G.nodes[destination_node]['x']), tooltip=(points[vehicule[i][j+1]]), icon=fm.Icon(color=colors[i-1])).add_to(features[i-1])
        route_map = ox.plot_route_folium(G, nx.shortest_path(G, origin_node, destination_node, weight='travel_time'), route_map=features[i-1], color=colors[i-1],weight=6,opacity=0.8,tooltip=amb)

        
fig, ax = ox.plot_graph_routes(G, routes, route_color='r', route_linewidth=6, node_size=0)

# Affichage sur folium
fm.LayerControl().add_to(m)
route_map.save('part2.html')