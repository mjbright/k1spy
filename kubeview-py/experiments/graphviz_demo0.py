#!/usr/bin/env /Users/mjb/scripts/HASHBANG_PYTHON3_venv.sh d3

import graphviz

f = graphviz.Digraph(filename = "output/plain organogram 1.gv")

names = ["A","B","C","D","E","F","G","H"]
positions = ["CEO","Team A Lead","Team B Lead", "Staff A","Staff B", "Staff C", "Staff D", "Staff E"]

for name, position in zip(names, positions):
     f.node(name, position)
 
#Specify edges
f.edge("A","B"); f.edge("A","C") #CEO to Team Leads
f.edge("B","D"); f.edge("B","E") #Team A relationship
f.edge("C","F"); f.edge("C","G"); f.edge("C","H") #Team B relationship
 
f
print(f.source)



