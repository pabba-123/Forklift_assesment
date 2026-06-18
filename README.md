Part A: Visualization (Bounding Boxes and Masks)
You must parse the XML file and draw bounding boxes and masks around the objects for every frame. The classes you need to plot are:
Each object class must be plotted using the exact color defined below.
Colors are specified in BGR format (as used by OpenCV).
Class Name	Description	Color Name	BGR Value (OpenCV)
forklift	Forklift body	Blue	(255, 0, 0)
forklift_pole	Vertical pole of forklift	Yellow	(0, 255, 255)
forklift_teeth	Forklift teeth/fork	Red	(0, 0, 255)
pallet	Wooden pallet	Green	(0, 255, 0)

Part B: The "Smart" Overlay
On the top-left of the video, you must draw a black background box with white text displaying the current status of the forklift.
Text Format:
Forklift {ID} Teeth Height: {Column}-{Row}
Example:
Forklift 1 Teeth 5-A
How to calculate the values:
1.	ID: This comes from the XML track ID (usually '1' for the main forklift).
2.	Column: For this specific demo, the column is fixed at 5 (the forklift does not move front/back, only the forks move up/down).
3.	Row :
a.	The "Row" represents the shelf height (A, B, C, or D).
b.	Row A: The lowest level (Ground level).
c.	Row D: The highest shelf level.
d.	Logic: As the Forklift Teeth (or the base of the Pallet if teeth aren’t visible) move up vertically, the Row changes from A --> B  --> C --> D.
e.	Your code must determine which Row the forklift is currently targeting based on the vertical (y-axis) position of the teeth/pallet.


For this assignment, I first parsed the CVAT XML annotation file using Python's built-in ElementTree library. The XML contains object tracks and polygon coordinates for each frame of the video. I organized this information frame-wise so that all annotations belonging to a particular frame could be accessed efficiently during video processing.

Next, I used OpenCV to read the input video frame by frame. For every frame, I retrieved the corresponding annotations from the parsed XML data and drew the required polygons, masks, and bounding boxes. Each object class was displayed using the color specified in the assignment requirements:

Forklift – Blue
Forklift Pole – Yellow
Forklift Teeth – Red
Pallet – Green

To improve visibility, I created semi-transparent masks by blending colored polygon regions with the original video frame while also drawing polygon outlines and bounding boxes.

For the smart overlay, I displayed the forklift status in the top-left corner of the video using a black background rectangle with white text. The forklift ID was obtained from the XML track information, while the column value was fixed at 5 as specified in the assignment.

To determine the shelf level (A, B, C, or D), I used the vertical position (Y-coordinate) of the forklift teeth. When the teeth were not available, the pallet position was used as a fallback. The video frame height was divided into four vertical zones representing the different shelf levels. As the teeth moved upward in the frame, the reported shelf level changed from A (ground level) to D (highest level).

Finally, each processed frame was written to a new output video file, producing a complete visualization with object annotations and real-time forklift status information.

Row (A/B/C/D) Logic

The shelf level is determined using the vertical position of the forklift teeth or pallet. Since objects higher in the warehouse appear closer to the top of the frame, smaller Y-coordinate values correspond to higher shelf levels.

The frame height was divided into four regions:

A → Ground level (lowest shelf)
B → Lower shelf
C → Middle shelf
D → Highest shelf

Based on the detected Y-coordinate, the appropriate shelf level is assigned and displayed in the overlay. This approach provides a simple and efficient way to estimate the forklift's target shelf level from the annotation data.