import numpy as np
import cv2

image = cv2.imread('test/card_0315.jpg')
assert image is not None, "file could not be read, check with os.path.exists()"


#imgray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
#ret, thresh = cv2.threshold(imgray, 127, 255, 0)
#contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

# Grayscale
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# Find Canny edges
edged = cv2.Canny(gray, 100, 200)

# Finding Contours
# Use a copy of the image e.g. edged.copy()
# since findContours alters the image
contours, hierarchy = cv2.findContours(edged, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_NONE)

cv2.imshow('Canny Edges After Contouring', edged)
cv2.waitKey(0)

print("Number of Contours found = " + str(len(contours)))

# Merge contours into one
list_of_pts = []
for ctr in contours:
    list_of_pts += [pt[0] for pt in ctr]
ctr = np.array(list_of_pts).reshape((-1,1,2)).astype(np.int32)
contours = ctr

image_copy = image.copy()
cv2.drawContours(image_copy, contours, -1, (0, 255, 0), 3)
cv2.imshow('Contours', image_copy)
cv2.waitKey(0)

contours = [cv2.convexHull(contours)]

print("Number of Contours found after merge = " + str(len(contours)))

# Draw all contours
# -1 signifies drawing all contours

cv2.drawContours(image, contours, -1, (0, 255, 0), 3)
cv2.imshow('Contours', image)
cv2.waitKey(0)
cv2.destroyAllWindows()
