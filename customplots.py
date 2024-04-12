# -*- coding: utf-8 -*-
"""
Created on Tue Apr  9 12:14:13 2024
@author: Patrick

"""

import matplotlib.pyplot as plt

# Function to declutter axes objects
def declutter(ax):
    ax.set_xlabel('');
    ax.set_ylabel('');
    ax.spines[['top','right','bottom','left']].set_visible(False)
    ax.tick_params(axis='x', which='both', bottom=False, top=False)
    ax.tick_params(axis='y', length=0)
    return ax

def customfont(size=12):
    custom_font = {'family': "Roboto", 'weight': 'regular', 'size': size}
    plt.rc('font',**custom_font)