#!/usr/bin/python

# PROJECT: SD Services Lab
# AUTHOR: Brad Sickler
# DATE MODIFIED: 2/6/15
#
# Copyright (c) 2015 Illumina
# This source file is covered by the "Illumina Public Source License"
# agreement and bound by the terms therein.
#
# Change Log:
# 1.2 Few tweaks for python 2 and 3 compatibility
# 1.1 Added file-path option to output
# 1.0 Ported Initial version from perl predecessor with a few extras :)

from __future__ import print_function
import os
import sys
import logging
import optparse
import gzip

__program_name__ = os.path.basename(__file__)

# Program details
__version__ = "1.2"
__author__ = "Brad Sickler"
__description__ = """Quick script to combine generic delimited reports.
If reports have different column headers attempts to recombine in roughly the same order.
"""
__usage__ = "python %s [options] file1.txt [file2.txt... *.txt]" % __program_name__

DEFAULT_DELIMITER = "\t"
DEFAULT_OUTPUT_DELIMITER = "\t"
DEFAULT_NA_VALUE = "None"


class FileHandler:
    """
    Class handles storing file headers and data
    """

    def __init__(self, delimiter):
        self.delimiter = delimiter
        self.file_name_arr = []
        self.file_data_mapping = {}
        self.header_mapping = HeaderMapper()

    def read_header(self, file_obj):
        header_string = ''
        while not header_string:
            line = file_obj.next().rstrip()
            if line[0] == '#' or line.isspace():
                continue
            header_string = line

        if not header_string:
            logging.warning("File is empty: %s" % file_obj.name)
            return False
        return header_string.split(self.delimiter)

    def get_output_array(self, null_value, output_file_name=False):
        final_header = self.header_mapping.get_header()

        out_array = [final_header]

        if output_file_name:
            out_array = [['file_path'] + final_header]

        for f_name in self.file_name_arr:
            out_array += self.file_data_mapping[f_name].get_ordered_output_array(ordered_array=final_header,
                                                                                 null_value=null_value,
                                                                                 output_file_name=output_file_name)
        return out_array

    def get_output_array_transposed(self, null_value, output_file_name=False):
        output_array = self.transpose_array(self.get_output_array(null_value=null_value,
                                                                  output_file_name=output_file_name))
        return output_array

    @staticmethod
    def transpose_array(array):
        return zip(*array)

    @staticmethod
    def open_file(file_path):
        if file_path[-3:] == '.gz':
            return gzip.open(file_path, 'r')
        else:
            return open(file_path, 'r')

    def add_file(self, added_file_path):
        logging.debug("Adding file %s" % added_file_path)
        file_obj = self.open_file(added_file_path)
        file_header = self.read_header(file_obj)
        if not file_header:
            logging.warning("Skipping file %s no header found!" % file_obj.name)
        self.file_name_arr.append(added_file_path)
        self.header_mapping.add_header_arr(file_header)
        self.file_data_mapping[added_file_path] = FileData(header_arr=file_header,
                                                           file_obj=file_obj,
                                                           delimiter=self.delimiter)
        file_obj.close()


class FileData:
    """
    Quick class to store file data.
    Expects the file_obj to be at the data point on init
    Siphons file data into file
    """

    def __init__(self, header_arr, file_obj, delimiter):
        self.file_name = file_obj.name
        self.header_arr = header_arr
        self.header_length = len(self.header_arr)
        self.delimiter = delimiter
        self.data_arr = []
        self.header_arr = header_arr

        self.read_data(file_obj)

    def read_data(self, file_obj):
        line_num = 1
        for line in file_obj:
            line_num += 1
            if line.isspace() or line[0] == '#':
                continue

            line_spl = line.rstrip("\n").rstrip("\r").split(self.delimiter)
            if not len(line_spl) == self.header_length:
                logging.error("SKIPPING: File %s row %s has inconsistent number of columns %s compared to header %s" %
                              (self.file_name, line_num, len(line_spl), self.header_length))
                continue
            self.data_arr.append({})
            for (col_num, column_id) in enumerate(self.header_arr):
                self.data_arr[-1][column_id] = line_spl[col_num]

    def get_ordered_output_array(self, ordered_array, null_value, output_file_name):
        """
        Returns an array of arrays ordered by the ordered_array with the null value inserted in for unknowns
        :rtype : list
        """
        out_array = []
        for line_dict in self.data_arr:
            out_array.append([])
            if output_file_name:
                out_array[-1].append(self.file_name)

            for column_id in ordered_array:
                if column_id in line_dict:
                    out_array[-1].append(line_dict[column_id])
                else:
                    out_array[-1].append(null_value)

        return out_array


class HeaderMapper:
    """
    Class handles ordering and management of header columns
    """

    def __init__(self):
        self.header_counts = {}  # Will hold dict of column_positions -> dict of column_id counts
        self.header_values = {}  # Will hold array of column positions

        self.header_order_final = []

    def add_header_arr(self, header_arr):
        for (column_num, column_id) in enumerate(header_arr):
            if column_num not in self.header_counts:
                self.header_counts[column_num] = {}
                logging.debug("Added column %s - %s" % (column_id, column_num))
            if column_id not in self.header_counts[column_num]:
                self.header_counts[column_num][column_id] = 0
            self.header_counts[column_num][column_id] += 1

            if column_id not in self.header_values:
                self.header_values[column_id] = []
            self.header_values[column_id].append(column_num)

    def get_header(self):
        if not self.header_order_final:
            self.set_final_header()
        return self.header_order_final

    def set_final_header(self):
        for column_num in sorted(self.header_counts):
            for column_id in sorted(self.header_counts[column_num],
                                    key=lambda x: self.header_counts[column_num][x],
                                    reverse=True):
                if column_id in self.header_order_final:
                    continue
                self.header_order_final.append(column_id)
                logging.debug("Assigned column %s to position %d" % (column_id, len(self.header_order_final)))

    def __str__(self):
        header_order_final = self.get_header()
        return_str = ''
        for (column_num, column_id) in enumerate(header_order_final):
            return_str += "Column: " + column_num + " = " + column_id + "\n"
        return return_str


def array_to_string(array, delimiter):
    out_string = ''
    for row in array:
        out_string += delimiter.join(row) + "\n"
    return out_string


def parse_options():
    """
    Parses the command line arguments.
    """
    opts = optparse.OptionParser(usage=__usage__, description=__description__, version=__version__)
    opts.add_option("--delimiter", "-d", dest="delimiter", type="string", default=DEFAULT_DELIMITER,
                    help="Delimiter to use. Default='%s'" % DEFAULT_DELIMITER)
    opts.add_option("--file-name", "-f", dest="output_file_name", action="store_true", default=False,
                    help="If set, will add file name to the first column. Default=False")
    opts.add_option("--na-value", "-n", dest="na_value", type="string", default=DEFAULT_NA_VALUE,
                    help="Default value to use for empty fields. Default='%s'" % DEFAULT_NA_VALUE)
    opts.add_option("--output-delimiter", "-o", dest="output_delimiter", default=DEFAULT_OUTPUT_DELIMITER,
                    help="Delimiter to use for output. Default='%s'" % DEFAULT_OUTPUT_DELIMITER)
    opts.add_option("--transpose", "-t", dest="transpose", action="store_true", default=False,
                    help="If set, will transpose the output!")
    opts.add_option("--verbose", "-v", dest="verbose", action="store_true", default=False,
                    help="Print out extra diagnostic information.")

    (options, arguments) = opts.parse_args()

    if not arguments:
        opts.print_help()
        logging.error("Must provide files to operate on. Usage: %s" % __usage__)
        sys.exit(1)

    for file_path in arguments:
        if not os.path.isfile(file_path):
            opts.print_help()
            logging.error("Unable to find file %s" % file_path)
            sys.exit(1)

    return options, arguments


# ------ Main Code Body
if __name__ == "__main__":
    (args, files) = parse_options()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    file_mapper = FileHandler(args.delimiter)

    for file_name in files:
        file_mapper.add_file(file_name)

    output_array = []
    if args.transpose:
        output_array = file_mapper.get_output_array_transposed(null_value=args.na_value,
                                                               output_file_name=args.output_file_name)
    else:
        output_array = file_mapper.get_output_array(null_value=args.na_value,
                                                    output_file_name=args.output_file_name)

    print(array_to_string(array=output_array,
                          delimiter=args.output_delimiter))
