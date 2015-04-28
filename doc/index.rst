.. Adagio documentation master file, created by
   sphinx-quickstart on Thu Jul 10 17:23:44 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. _index:


====================================================
Structural Analysis and Detection of Android Malware 
====================================================

Adagio contains several modules that implement the method described in the
paper_:

    | **Structural Detection of Android Malware using Embedded Call Graphs**
    | Hugo Gascon, Fabian Yamaguchi, Daniel Arp, Konrad Rieck
    | *ACM Workshop on Security and Artificial Intelligence (AISEC) November 2013*

.. _paper: http://user.informatik.uni-goettingen.de/~hgascon/docs/2013b-aisec.pdf

These modules allow to extract and label the call graphs from a series of
Android APKs or DEX files and apply an explicit feature map that captures
their structural relationships. The analysis module provides classes to desing a binary
or multiclass classification experiment using the vectorial representation and
support vector machines.

Having troubles?
================

If you are having troubles running the code, you are welcome to drop a message_.

.. _message: https://github.com/hgascon/adagio/issues

Content
=======

.. toctree::

    introduction
    installation
    usage
