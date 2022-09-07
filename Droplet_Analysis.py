# @ File[] (label="Input directory", style="both") inputs
# @ File (label="Output directory", style="directory") outputdir 
# @ Integer (label="Channel with droplets ", min=1, max=7, value=1) ch_no
# @ Double (label="Min droplet area ", min=0.001, stepSize=0.01, value=0.1) min_area
# @ Double (label="Max droplet area ", min=0.001, stepSize=0.01, value=10.0) max_area
# @ Boolean (label="Save binary mask", default=False, required=False) save_mask
# @ Boolean (label="Show images", default=False, required=False) show_images

import sys
import math

from ij import IJ, Prefs, ImagePlus
from loci.plugins import BF
from loci.plugins.in import ImporterOptions
from ij.plugin.frame import RoiManager
from ij.plugin import Duplicator, ZProjector

import os

def read_dir(directory, ext):
    files = os.listdir(directory)
    img_files = [os.path.join(directory,f) for f in files if f.split(".")[-1] in ext]
    return img_files

def get_files(inputs, ext=["czi"]):
    img_files = [read_dir(str(f), ext) if os.path.isdir(str(f)) else [str(f)] for f in inputs]
    flat_filtered = [f for l in img_files for f in l if f.split(".")[-1] in ext]
    exists = [f for f in flat_filtered if os.path.exists(f)]
    return exists

def open_image(imgfile):
	options = ImporterOptions()
	options.setId(imgfile)
	options.setSplitChannels(False)
	options.setColorMode(ImporterOptions.COLOR_MODE_COMPOSITE)
	imps = BF.openImagePlus(options)
	return imps[0]

def process(imagestack, min_area, max_area, ch_no=1, zstart=1, zend=None, tstart=1, tend=None):
    rm = RoiManager.getRoiManager()
    title = imagestack.getTitle()
    
    zend = imagestack.getDimensions()[3] if zend is None else zend
    tend = imagestack.getDimensions()[4] if tend is None else tend
    imp = Duplicator().run(imagestack, ch_no, ch_no, zstart, zend, tstart, tend) 
    imp = ZProjector.run(imp, "max",1, 25) # is this last frame or slice?
    imp.setTitle(title)
    
    mask = imp.duplicate()
    IJ.setAutoThreshold(mask, "Yen")
    Prefs.blackBackground = False
    IJ.run(mask, "Convert to Mask", "")
    IJ.run(mask, "Invert", "")
    IJ.run("Set Measurements...", "area mean min centroid integrated display decimal=3")
    IJ.run(
        mask, 
        "Analyze Particles...", 
        "size="+str(min_area)+"-"+str(max_area) + "add"
    )
    rm.runCommand(imp, "Measure")
    mask.setTitle(".".join(title.split(".")[:-1])+"-mask")
    return mask

def save_image(img, outputdir, suffix=""):
    filename = img.getTitle().split(".")[0]+suffix+".tif"
    path = os.path.join(outputdir, filename)
    IJ.saveAsTiff(img, path)
    print "Saved mask as", filename
    
# Main code
outputdir = str(outputdir)
if not os.path.isdir(outputdir):
    os.makedirs(outputdir)
	
img_files = get_files(inputs)
if show_images and len(img_files) > 5:
    print "Ignoring show_images flag."
    show_images = False
    
for item in img_files:
    try:
        img = open_image(item)
        dims = img.getDimensions()
        print 'Processing', item, "-", dims[2],"channel[s],", dims[3], "slice[s],", dims[4], "frame[s]"
        mask = process(img, min_area, max_area, ch_no=ch_no, zend=19, tend=1)
        if show_images:
            img.show()
            mask.show()
        if save_mask:
            save_image(mask, outputdir)
    except:
        print 'Error, skipping', item
print 'Done.\n'
