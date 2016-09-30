# Copyright (C) Nial Peters 2009
#
# This file is part of pysces_asi.
#
# pysces_asi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
# pysces_asi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pysces_asi.  If not, see <http://www.gnu.org/licenses/>.
"""
This module defines a few functions used to create outputs by pysces_asi. See the README file
for details on producing outputs.
"""

import os
import shutil
import datetime
import sys
import logging

from PASKIL import allskyKeo, allskyPlot
from pysces_asi.output_task_handler import register


log = logging.getLogger("outputs")
##########################################################################


def copy_image(image, output, settings_manager):
    source_path = image.getFilename()
    source_filename = os.path.basename(source_path)
    file_, extension = os.path.splitext(source_filename)

    day_folder = settings_manager.get(["output folder"])["output folder"]

    dest_path = os.path.normpath(
        day_folder + "/" + output.folder_on_host + "/" + file_ + extension)

    # copy the image
    settings_manager.set(
        {"output": "OutputTaskHandler> Copying " + source_path + " to " + dest_path})
    shutil.copyfile(source_path, dest_path)

    return None

##########################################################################


def create_quicklook(image, output, settings_manager):
    settings_manager.set(
        {'output': "OutputTaskHandler> Creating quicklook for " + image.getFilename()})
    im = image.binaryMask(output.fov_angle)
    im = im.centerImage()
    im = im.alignNorth(north="geomagnetic", orientation='NWSE')
    if hasattr(output, "label"):
        ql = im.createQuicklook(label=output.label)
    else:
        ql = im.createQuicklook()

    return ql

##########################################################################


def centered_image(image, output, settings_manager):
    settings_manager.set(
        {'output': "OutputTaskHandler> Creating centered image for " + image.getFilename()})
    im = image.binaryMask(output.fov_angle)
    im = im.centerImage()
    im = im.alignNorth(north="geomagnetic", orientation='NWSE')
    log.info("Made image ")
    return im

##########################################################################


def check_keo_compatibility(keo, image, output):
    """
    Checks that an image has compatible properties with the realtime keogram. Although
    PASKIL can cope with putting images of different properties into keograms, unless a 
    check is made, the realtime keogram will always keep its old properties. For example,
    if the original keogram had a field of view of 90, and then it got changed to 75, the
    keogram scale would always go to 90, but it would be filled in black - better just to 
    create a new keogram that will look right.
    """
    # first check if output settings have changed
    keo_time_width = (keo.getEnd_time() - keo.getStart_time())
    keo_time_width_hours = (
        keo_time_width.days * 24) + (keo_time_width.seconds / 3600.0)

    if ((output.strip_width != keo.getStrip_width()) or
            (output.data_spacing != keo.getDataSpacing()) or
            (output.time_range != keo_time_width_hours) or
            (output.angle != keo.getAngle()) or
            (output.fov_angle != keo.getFov_angle())):
        return False

    # next check the image properties
    im_info = image.getInfo()
    try:
        im_abs_calib = im_info['processing']['absoluteCalibration']
    except KeyError:
        im_abs_calib = None

    if ((image.getMode() != keo.getMode()) or
            #(im_info['header']['Wavelength'] != keo.getWavelength() or
            (image.getColourTable() != keo.getColour_table()) or
            (im_info['camera']['lens_projection'] != keo.getLens_projection()) or
            (im_abs_calib != keo.getCalib_factor())):
        # don't need to compare the image fov angle, only that set for the
        # keogram
        return False
    return True

 ##########################################################################


def realtime_keogram(image, output, settings_manager):

    # see if a realtime keogram has been created yet
    log.info("starting keogram")
    try:
        filename = settings_manager.get(
            ['user_rt_keo_name'])['user_rt_keo_name']
    except KeyError:
        filename = None
    image = image.resize((500, 500))

    if filename is None or not os.path.exists(filename):
        settings_manager.set(
            {'output': "OutputTaskHandler> Creating new realtime keogram."})
        # work out the start and end times for the keogram based on the setting
        # in the settings file
        end_time = datetime.datetime.utcnow()
        time_span = datetime.timedelta(hours=output.time_range)
        start_time = end_time - time_span

        keo = allskyKeo.new([image], output.angle, start_time, end_time, strip_width=output.strip_width,
                            data_spacing=output.data_spacing, keo_fov_angle=output.fov_angle)

        try:
            keo.save(os.path.expanduser('~') + "/realtime_keogram")
            settings_manager.create('user_rt_keo_name', os.path.expanduser(
                '~') + "/realtime_keogram", persistant=True)
        except ValueError:
            # value already exists - just update it to the new value
	    print("Unexpected error:", sys.exc_info()[0])
            settings_manager.set(
                {'user_rt_keo_name': os.path.expanduser('~') + "/realtime_keogram"})
    else:
        log.info("Opening keogram")
        try:
            keo = allskyKeo.load(filename)
	except IOError: 
	    print("Unexpected error:", sys.exc_info()[0])
	    print(filename)
        except:
            print("Unexpected error:", sys.exc_info()[0])
        settings_manager.set(
            {'output': "OutputTaskHandler> Adding image to realtime keogram."})

        # check that the image (and output settings) is actually compatible with the current
        # keogram - for example if the FOV has changed we don't want the range on the keogram
        # to always be out of date.

        if check_keo_compatibility(keo, image, output):
            keo = keo.roll([image])
            try:
                keo.save(filename)
            except:
                print("Unexpected error:", sys.exc_info()[0])
        else:
            # some of the settings must have changed - time to start a new
            # keogram
            settings_manager.set(
                {'user_rt_keo_name': None, 'output': "OutputTaskHandler> New image is not compatible with existing keogram."})
            return realtime_keogram(image, output, settings_manager)
        log.info("made keogram")

    return allskyPlot.plot([keo], size=(9, 3.7))

##########################################################################

# dict to map output types to output functions.
register("raw", copy_image)
register("quicklook", create_quicklook)
register("paskil_png", centered_image)
register("realtimeKeo", realtime_keogram)
