# -*- coding: utf-8 -*-
"""
Custom checkbox indicator helper for SundPood
Adds checkmark icon to checkboxes programmatically
"""

from PyQt5 import QtCore, QtGui, QtWidgets


def style_checkbox(checkbox):
    """
    Apply custom styling to make checked state more visible
    Adds a checkmark prefix to the checkbox text when checked
    """
    # Store original text if not already stored
    original_text = checkbox.text().lstrip("✓ ")
    checkbox.setProperty("original_text", original_text)
    
    # When checkbox state changes, update its appearance
    def update_appearance(state):
        orig_text = checkbox.property("original_text")
        if not orig_text:
            orig_text = checkbox.text().lstrip("✓ ")
            checkbox.setProperty("original_text", orig_text)
        
        if state == QtCore.Qt.Checked:
            # Add checkmark emoji to text for visual feedback
            if not checkbox.text().startswith("✓ "):
                checkbox.setText(f"✓ {orig_text}")
        else:
            # Remove checkmark
            checkbox.setText(orig_text)
    
    checkbox.stateChanged.connect(update_appearance)
    # Update initial state
    update_appearance(checkbox.checkState())

