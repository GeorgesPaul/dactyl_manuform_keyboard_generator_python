import cadquery as cq

pts = [
       cq.Vector([20, 20 ,20]), 
       cq.Vector([-20, 20, 15]), 
       cq.Vector([20, -20, 30]), 
       cq.Vector([-20, -20, 5]),
       ]

result = cq.makeSpline(pts)
#result = cq.Workplane("XY" ).box(3, 3, 0.5).edges("|Z").fillet(0.125)