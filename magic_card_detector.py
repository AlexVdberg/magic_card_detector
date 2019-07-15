"""
Module for detecting and recognizing Magic: the Gathering cards from an image.
"""

import glob
import cProfile
import pstats
import io
from itertools import product

import numpy as np
import matplotlib.pyplot as plt

from shapely.geometry import Point, LineString
from shapely.geometry.polygon import Polygon
from shapely.affinity import scale
from scipy.ndimage import rotate
from PIL import Image as PILImage

import imagehash
import cv2


def order_points(pts):
    """
    Orders polygon points for the perspective transform.
    """
    # initialize a list of coordinates that will be ordered
    # such that the first entry in the list is the top-left,
    # the second entry is the top-right, the third is the
    # bottom-right, and the fourth is the bottom-left
    rect = np.zeros((4, 2), dtype="float32")

    # the top-left point will have the smallest sum, whereas
    # the bottom-right point will have the largest sum
    rect[0] = pts[np.argmin(pts.sum(axis=1))]
    rect[2] = pts[np.argmax(pts.sum(axis=1))]

    # now, compute the difference between the points, the
    # top-right point will have the smallest difference,
    # whereas the bottom-left will have the largest difference
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    # return the ordered coordinates
    return rect


def order_polygon_points(x_p, y_p):
    """
    Orders polygon points into a counterclockwise order.
    x_p, y_p are the x and y coordinates of the polygon points.
    """
    angle = np.arctan2(y_p - np.average(y_p), x_p - np.average(x_p))
    ind = np.argsort(angle)
    return (x_p[ind], y_p[ind])


def four_point_transform(image, poly):
    """
    A perspective transform for a quadrilateral polygon.
    """
    pts = np.zeros((4, 2))
    pts[:, 0] = np.asarray(poly.exterior.coords)[:-1, 0]
    pts[:, 1] = np.asarray(poly.exterior.coords)[:-1, 1]
    # obtain a consistent order of the points and unpack them
    # individually
    rect = np.zeros((4, 2))
    (rect[:, 0], rect[:, 1]) = order_polygon_points(pts[:, 0], pts[:, 1])

    # compute the width of the new image, which will be the
    # maximum distance between bottom-right and bottom-left
    # x-coordiates or the top-right and top-left x-coordinates
    # width_a = np.sqrt(((b_r[0] - b_l[0]) ** 2) + ((b_r[1] - b_l[1]) ** 2))
    # width_b = np.sqrt(((t_r[0] - t_l[0]) ** 2) + ((t_r[1] - t_l[1]) ** 2))
    width_a = np.sqrt(((rect[1, 0] - rect[0, 0]) ** 2) +
                      ((rect[1, 1] - rect[0, 1]) ** 2))
    width_b = np.sqrt(((rect[3, 0] - rect[2, 0]) ** 2) +
                      ((rect[3, 1] - rect[2, 1]) ** 2))
    max_width = max(int(width_a), int(width_b))

    # compute the height of the new image, which will be the
    # maximum distance between the top-right and bottom-right
    # y-coordinates or the top-left and bottom-left y-coordinates
    height_a = np.sqrt(((rect[0, 0] - rect[3, 0]) ** 2) +
                       ((rect[0, 1] - rect[3, 1]) ** 2))
    height_b = np.sqrt(((rect[1, 0] - rect[2, 0]) ** 2) +
                       ((rect[1, 1] - rect[2, 1]) ** 2))
    max_height = max(int(height_a), int(height_b))

    # now that we have the dimensions of the new image, construct
    # the set of destination points to obtain a "birds eye view",
    # (i.e. top-down view) of the image, again specifying points
    # in the top-left, top-right, bottom-right, and bottom-left
    # order

    rect = np.array([
        [rect[0, 0], rect[0, 1]],
        [rect[1, 0], rect[1, 1]],
        [rect[2, 0], rect[2, 1]],
        [rect[3, 0], rect[3, 1]]], dtype="float32")

    dst = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1]], dtype="float32")

    # compute the perspective transform matrix and then apply it
    transform = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, transform, (max_width, max_height))

    # return the warped image
    return warped


def line_intersection(x, y):
    """
    Calculates the intersection point of two lines, defined by the points
    (x1, y1) and (x2, y2) (first line), and
    (x3, y3) and (x4, y4) (second line).
    If the lines are parallel, (nan, nan) is returned.
    """
    if (x[0] - x[1]) * (y[2] - y[3]) == (y[0] - y[1]) * (x[2] - x[3]):
        # parallel lines
        xis = np.nan
        yis = np.nan
    else:
        xis = ((x[0] * y[1] - y[0] * x[1]) * (x[2] - x[3]) -
               (x[0] - x[1]) * (x[2] * y[3] - y[2] * x[3])) / \
              ((x[0] - x[1]) * (y[2] - y[3]) - (y[0] - y[1]) * (x[2] - x[3]))

        yis = ((x[0] * y[1] - y[0] * x[1]) * (y[2] - y[3]) -
               (y[0] - y[1]) * (x[2] * y[3] - y[2] * x[3])) / \
              ((x[0] - x[1]) * (y[2] - y[3]) - (y[0] - y[1]) * (x[2] - x[3]))
    return (xis, yis)


def simplify_polygon(in_poly, tol=0.05, maxiter=None, segment_to_remove=None):
    """
    Removes segments from a (convex) polygon by continuing neighboring
    segments to a new point of intersection. Purpose is to approximate
    rounded polygons (quadrilaterals) with more sharp-cornered ones.
    """

    x_in = np.asarray(in_poly.exterior.coords)[:-1, 0]
    y_in = np.asarray(in_poly.exterior.coords)[:-1, 1]
    len_poly = len(x_in)
    niter = 0
    if segment_to_remove is not None:
        maxiter = 1
    while len_poly > 4:
        d_in = np.sqrt(np.ediff1d(x_in, to_end=x_in[0]-x_in[-1]) ** 2.
                       + np.ediff1d(y_in, to_end=y_in[0]-y_in[-1]) ** 2.)
        d_tot = np.sum(d_in)
        if segment_to_remove is not None:
            k = segment_to_remove
        else:
            k = np.argmin(d_in)
        if d_in[k] < tol * d_tot:
            ind = generate_point_indices(k - 1, k + 1, len_poly)
            (xis, yis) = line_intersection(x_in[ind], y_in[ind])

            x_in[k] = xis
            y_in[k] = yis
            x_in = np.delete(x_in, (k+1) % len_poly)
            y_in = np.delete(y_in, (k+1) % len_poly)
            len_poly = len(x_in)
            niter += 1
            if (maxiter is not None) and (niter >= maxiter):
                break
        else:
            break

    out_poly = Polygon([[ix, iy] for (ix, iy) in zip(x_in, y_in)])

    return out_poly


def generate_point_indices(index_1, index_2, max_len):
    """
    Returns the four indices that give the end points of
    polygon segments corresponding to index_1 and index_2,
    modulo the number of points (max_len).
    """
    return np.array([index_1 % max_len,
                     (index_1 + 1) % max_len,
                     index_2 % max_len,
                     (index_2 + 1) % max_len])


def generate_quad_corners(indices, x_s, y_s):
    """
    Returns the four intersection points from the
    segments defined by the x coordinates (x_s),
    y coordinates (y_s), and the indices.
    """
    (i, j, k, l) = indices

    def gpi(index_1, index_2):
        return generate_point_indices(index_1, index_2, len(x_s))

    xis = np.empty(4)
    yis = np.empty(4)
    xis.fill(np.nan)
    yis.fill(np.nan)

    if j <= i or k <= j or l <= k:
        pass
    else:
        (xis[0], yis[0]) = line_intersection(x_s[gpi(i, j)],
                                             y_s[gpi(i, j)])
        (xis[1], yis[1]) = line_intersection(x_s[gpi(j, k)],
                                             y_s[gpi(j, k)])
        (xis[2], yis[2]) = line_intersection(x_s[gpi(k, l)],
                                             y_s[gpi(k, l)])
        (xis[3], yis[3]) = line_intersection(x_s[gpi(l, i)],
                                             y_s[gpi(l, i)])

    return (xis, yis)


def generate_quad_candidates(in_poly):
    """
    Generates a list of bounding quadrilaterals for a polygon,
    using all possible combinations of four intersection points
    derived from four extended polygon segments.
    The number of combinations increases rapidly with the order
    of the polygon, so simplification should be applied first to
    remove very short segments from the polygon.
    """

    # make sure that the points are ordered
    (x_s, y_s) = order_polygon_points(
        np.asarray(in_poly.exterior.coords)[:-1, 0],
        np.asarray(in_poly.exterior.coords)[:-1, 1])
    quads = []
    len_poly = len(x_s)

    for indices in product(range(len_poly), repeat=4):
        (xis, yis) = generate_quad_corners(indices, x_s, y_s)
        if (np.sum(np.isnan(xis)) + np.sum(np.isnan(yis))) > 0:
            # no intersection point for some of the lines
            pass
        else:
            xis_ave = np.average(xis)
            yis_ave = np.average(yis)
            xis = xis_ave + 1.0001 * (xis - xis_ave)
            yis = yis_ave + 1.0001 * (yis - yis_ave)
            (xis, yis) = order_polygon_points(xis, yis)
            enclose = True
            quad = Polygon([(xis[0], yis[0]),
                            (xis[1], yis[1]),
                            (xis[2], yis[2]),
                            (xis[3], yis[3])])
            for x_i, y_i in zip(x_s, y_s):
                if (not quad.intersects(Point(x_i, y_i)) and
                        not quad.touches(Point(x_i, y_i))):
                    enclose = False
            if enclose:
                quads.append(quad)
    return quads


def get_bounding_quad(hull_poly):
    """
    Returns the minimum area quadrilateral that contains (bounds)
    the convex hull (openCV format) given as input.
    """
    simple_poly = simplify_polygon(hull_poly)
    bounding_quads = generate_quad_candidates(simple_poly)
    bquad_areas = np.zeros(len(bounding_quads))
    for iquad, bquad in enumerate(bounding_quads):
        bquad_areas[iquad] = bquad.area
    min_area_quad = bounding_quads[np.argmin(bquad_areas)]

    return min_area_quad


def quad_corner_diff(hull_poly, bquad_poly, region_size=0.9):
    """
    Returns the difference between areas in the corners of a rounded
    corner and the aproximating sharp corner quadrilateral.
    region_size (param) determines the region around the corner where
    the comparison is done.
    """
    bquad_corners = np.zeros((4, 2))
    bquad_corners[:, 0] = np.asarray(bquad_poly.exterior.coords)[:-1, 0]
    bquad_corners[:, 1] = np.asarray(bquad_poly.exterior.coords)[:-1, 1]

    # The point inside the quadrilateral, region_size towards the quad center
    interior_points = np.zeros((4, 2))
    interior_points[:, 0] = np.average(bquad_corners[:, 0]) + \
        region_size * (bquad_corners[:, 0] - np.average(bquad_corners[:, 0]))
    interior_points[:, 1] = np.average(bquad_corners[:, 1]) + \
        region_size * (bquad_corners[:, 1] - np.average(bquad_corners[:, 1]))

    # The points p0 and p1 (at each corner) define the line whose intersections
    # with the quad together with the corner point define the triangular
    # area where the roundness of the convex hull in relation to the bounding
    # quadrilateral is evaluated.
    # The line (out of p0 and p1) is constructed such that it goes through the
    # "interior_point" and is orthogonal to the line going from the corner to
    # the center of the quad.
    p0_x = interior_points[:, 0] + \
        (bquad_corners[:, 1] - np.average(bquad_corners[:, 1]))
    p1_x = interior_points[:, 0] - \
        (bquad_corners[:, 1] - np.average(bquad_corners[:, 1]))
    p0_y = interior_points[:, 1] - \
        (bquad_corners[:, 0] - np.average(bquad_corners[:, 0]))
    p1_y = interior_points[:, 1] + \
        (bquad_corners[:, 0] - np.average(bquad_corners[:, 0]))

    corner_area_polys = []
    for i in range(len(interior_points[:, 0])):
        bline = LineString([(p0_x[i], p0_y[i]), (p1_x[i], p1_y[i])])
        corner_area_polys.append(Polygon(
            [bquad_poly.intersection(bline).coords[0],
             bquad_poly.intersection(bline).coords[1],
             (bquad_corners[i, 0], bquad_corners[i, 1])]))

    hull_corner_area = 0
    quad_corner_area = 0
    for capoly in corner_area_polys:
        quad_corner_area += capoly.area
        hull_corner_area += capoly.intersection(hull_poly).area

    return 1. - hull_corner_area/quad_corner_area


def convex_hull_polygon(contour):
    """
    Returns the convex hull of the given contour as a polygon.
    """
    hull = cv2.convexHull(contour)
    phull = Polygon([[x, y] for (x, y) in
                     zip(hull[:, :, 0], hull[:, :, 1])])
    return phull


def polygon_form_factor(poly):
    """
    The ratio between the polygon area and circumference length,
    scaled by the length of the shortest segment.
    """
    # minimum side length
    d_0 = np.amin(np.sqrt(np.sum(np.diff(np.asarray(poly.exterior.coords),
                                         axis=0) ** 2., axis=1)))
    return poly.area/(poly.length * d_0)

#
# CLASSES
#


class CardCandidate:
    """
    Class representing a segment of the image that may be a recognizable card.
    """

    def __init__(self, im_seg, card_cnt, bquad, fraction):
        self.image = im_seg
        self.contour = card_cnt
        self.bounding_quad = bquad
        self.is_recognized = False
        self.is_fragment = False
        self.image_area_fraction = fraction
        self.name = 'unknown'

    def contains(self, other):
        """
        Returns whether the bounding polygon of the card candidate
        contains the bounding polygon of the other candidate.
        """
        return other.bounding_quad.within(self.bounding_quad)


class ReferenceImage:
    """
    Container for a card image and the associated recoginition data.
    """

    def __init__(self, name, original_image, clahe):
        self.name = name
        self.original = original_image
        self.clahe = clahe
        self.adjusted = None
        self.phash = None

        self.histogram_adjust()
        self.calculate_phash()

    def calculate_phash(self):
        """
        Calculates the perceptive hash for the image
        """
        self.phash = imagehash.phash(
                        PILImage.fromarray(np.uint8(255 * cv2.cvtColor(
                            self.adjusted, cv2.COLOR_BGR2RGB))),
                        hash_size=32)

    def histogram_adjust(self):
        """
        Adjusts the image by contrast limited histogram adjustmend (clahe)
        """
        lab = cv2.cvtColor(self.original, cv2.COLOR_BGR2LAB)
        lightness, redness, yellowness = cv2.split(lab)
        corrected_lightness = self.clahe.apply(lightness)
        limg = cv2.merge((corrected_lightness, redness, yellowness))
        self.adjusted = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)


class TestImage:
    """
    Container for a card image and the associated recoginition data.
    """

    def __init__(self, name, original_image, clahe):
        self.name = name
        self.original = original_image
        self.clahe = clahe
        self.adjusted = None
        self.phash = None
        self.visual = True
        self.histogram_adjust()
        # self.calculate_phash()

        self.candidate_list = []

    def histogram_adjust(self):
        """
        Adjusts the image by contrast limited histogram adjustmend (clahe)
        """
        lab = cv2.cvtColor(self.original, cv2.COLOR_BGR2LAB)
        lightness, redness, yellowness = cv2.split(lab)
        corrected_lightness = self.clahe.apply(lightness)
        limg = cv2.merge((corrected_lightness, redness, yellowness))
        self.adjusted = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

    def plot_image_with_recognized(self):
        """
        Plots the recognized cards into the full image.
        """
        # Plotting
        for candidate in self.candidate_list:
            if not candidate.is_fragment:
                full_image = self.adjusted
                bquad_corners = np.empty((4, 2))
                bquad_corners[:, 0] = np.asarray(
                    candidate.bounding_quad.exterior.coords)[:-1, 0]
                bquad_corners[:, 1] = np.asarray(
                    candidate.bounding_quad.exterior.coords)[:-1, 1]

                plt.plot(np.append(bquad_corners[:, 0],
                                   bquad_corners[0, 0]),
                         np.append(bquad_corners[:, 1],
                                   bquad_corners[0, 1]), 'g-')
                bounding_poly = Polygon([[x, y] for (x, y) in
                                         zip(bquad_corners[:, 0],
                                             bquad_corners[:, 1])])
                fntsze = int(4 * bounding_poly.length / full_image.shape[1])
                bbox_color = 'white' if candidate.is_recognized else 'red'
                plt.text(np.average(bquad_corners[:, 0]),
                         np.average(bquad_corners[:, 1]),
                         candidate.name,
                         horizontalalignment='center',
                         fontsize=fntsze,
                         bbox=dict(facecolor=bbox_color,
                                   alpha=0.7))

        plt.savefig('results/MTG_card_recognition_results_' +
                    str(self.name.split('.jpg')[0]) +
                    '.jpg', dpi=600, bbox='tight')
        if self.visual:
            plt.show()


class MTGCardDetector:
    """
    MTG card detector class.
    """

    def __init__(self):
        #self.ref_img_clahe = []
        #self.ref_filenames = []
        #self.test_img_clahe = []
        #self.test_filenames = []
        #self.warped_list = []
        #self.card_list = []
        #self.bounding_poly_list = []

        self.reference_images = []
        self.test_images = []
        #self.candidate_list = []

        #self.phash_ref = []

        self.verbose = False
        self.visual = True

        self.hash_separation_thr = 4.
        self.thr_lvl = 70

        self.clahe = cv2.createCLAHE(clipLimit=2.0,
                                     tileGridSize=(8, 8))

    def read_and_adjust_reference_images(self, path):
        """
        Reads and histogram-adjusts the reference image set.
        Pre-calculates the hashes of the images.
        """
        print('Reading images from ' + str(path))
        filenames = glob.glob(path + '*.jpg')
        for filename in filenames:
            img = cv2.imread(filename)
            img_name = filename.split(path)[1]
            self.reference_images.append(
                ReferenceImage(img_name, img, self.clahe))

    def read_and_adjust_test_images(self, path):
        """
        Reads and histogram-adjusts the test image set.
        """
        print('Reading images from ' + str(path))
        filenames = glob.glob(path + '*.jpg')
        for filename in filenames:
            img = cv2.imread(filename)
            img_name = filename.split(path)[1]
            self.test_images.append(
                TestImage(img_name, img, self.clahe))

    def segment_image(self, test_image):
        """
        Segments the given image into card candidates, that is,
        regions of the image that have a high chance
        of containing a recognizable card.
        """
        full_image = test_image.adjusted.copy()
        image_area = full_image.shape[0] * full_image.shape[1]
        lca = 0.01  # largest card area

        # grayscale transform, thresholding, countouring and sorting by area
        gray = cv2.cvtColor(full_image, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, self.thr_lvl, 255, cv2.THRESH_BINARY)
        _, contours, _ = cv2.findContours(
            np.uint8(thresh), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        for card_contour in contours:
            phull = convex_hull_polygon(card_contour)
            if phull.area < 0.7 * lca or phull.area < image_area / 1000.:
                # break after card size range has been explored
                break
            bounding_poly = get_bounding_quad(phull)

            qc_diff = quad_corner_diff(phull, bounding_poly)
            scale_factor = min(1., (1. - qc_diff * 22. / 100.))
            warped = four_point_transform(full_image,
                                          scale(bounding_poly,
                                                xfact=scale_factor,
                                                yfact=scale_factor,
                                                origin='centroid'))

            if (0.7 * lca < bounding_poly.area < image_area * 0.99 and
                    qc_diff < 0.35 and
                    0.27 < polygon_form_factor(bounding_poly) < 0.32):
                if lca == 0.01:
                    lca = bounding_poly.area
                test_image.candidate_list.append(
                    CardCandidate(warped,
                                  card_contour,
                                  bounding_poly,
                                  bounding_poly.area / image_area))
                print('Segmented ' +
                      str(len(test_image.candidate_list)) +
                      ' candidates.')

    def phash_compare(self, im_seg):
        """
        Runs perceptive hash comparison between given image and
        the (pre-hashed) reference set.
        """

        card_name = 'unknown'
        is_recognized = False
        rotations = np.array([0., 90., 180., 270.])

        d_0_dist = np.zeros(len(rotations))
        d_0 = np.zeros((len(self.reference_images), len(rotations)))
        for j, rot in enumerate(rotations):
            phash_im = imagehash.phash(PILImage.fromarray(
                np.uint8(255 * cv2.cvtColor(rotate(im_seg, rot),
                                            cv2.COLOR_BGR2RGB))), hash_size=32)
            for i in range(len(d_0)):
                d_0[i, j] = phash_im - self.reference_images[i].phash
            d_0_ = d_0[:, j][d_0[:, j] > np.amin(d_0[:, j])]
            d_0_ave = np.average(d_0_)
            d_0_std = np.std(d_0_)
            d_0_dist[j] = (d_0_ave - np.amin(d_0[:, j]))/d_0_std
            if self.verbose:
                print('Phash statistical distance' + str(d_0_dist[j]))
            if (d_0_dist[j] > self.hash_separation_thr and
                    np.argmax(d_0_dist) == j):
                card_name = self.reference_images[np.argmin(d_0[:, j])]\
                            .name.split('.jpg')[0]
                is_recognized = True
                break
        return (is_recognized, card_name)

    def recognize_segment(self, image_segment):
        """
        Wrapper for different segmented image recognition algorithms.
        """
        return self.phash_compare(image_segment)

    def run_recognition(self, image_index):
        """
        Tries to recognize cards from the image specified.
        The image has been read in and adjusted previously,
        and is contained in the internal data list of the class.
        """

        test_image = self.test_images[image_index]

        if self.visual:
            print('Original image')
            plt.imshow(cv2.cvtColor(test_image.original,
                                    cv2.COLOR_BGR2RGB))
            plt.show()

        print('Segmentation of art')

        test_image.candidate_list.clear()
        self.segment_image(test_image)

        print('Recognition')

        iseg = 0
        plt.imshow(cv2.cvtColor(test_image.original, cv2.COLOR_BGR2RGB))
        plt.axis('off')

        for candidate in test_image.candidate_list:
            im_seg = candidate.image

            iseg += 1
            print(str(iseg) + " / " +
                  str(len(test_image.candidate_list)))

            for other_candidate in test_image.candidate_list:
                if (other_candidate.is_recognized and
                        not other_candidate.is_fragment):
                    if other_candidate.contains(candidate):
                        candidate.is_fragment = True
            if not candidate.is_fragment:
                (candidate.is_recognized,
                 candidate.name) = self.recognize_segment(im_seg)

        test_image.plot_image_with_recognized()


def main():
    """
    Python MTG Card Detector.
    Example run.
    Can be used also purely through the defined classes.
    """

    # Instantiate the detector
    card_detector = MTGCardDetector()

    # Read the reference and test data sets
    card_detector.read_and_adjust_reference_images(
        '../../MTG/Card_Images/LEA/')
    card_detector.read_and_adjust_test_images('../MTG_alpha_test_images/')

    # Start up the profiler.
    profiler = cProfile.Profile()
    profiler.enable()

    # Run the card detection and recognition.
    for im_ind in range(1, 4):
        card_detector.run_recognition(im_ind)

    # Stop profiling and organize and print profiling results.
    profiler.disable()
    profiler_stream = io.StringIO()
    sortby = pstats.SortKey.CUMULATIVE
    profiler_stats = pstats.Stats(
        profiler, stream=profiler_stream).sort_stats(sortby)
    profiler_stats.print_stats(20)
    print(profiler_stream.getvalue())


if __name__ == "__main__":
    main()