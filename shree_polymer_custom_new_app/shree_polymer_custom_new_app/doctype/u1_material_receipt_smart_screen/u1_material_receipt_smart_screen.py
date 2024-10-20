# Copyright (c) 2024, Mazeworks Solutions Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class U1MaterialReceiptSmartScreen(Document):
    def on_submit(self):
        # Loop through items in the child table (assuming it's called 'items')
        for item in self.items:
            item_code = item.item_code
            dc_qty = float(item.qty_kg or 0)  # Quantity in Delivery Challan (Earlier Scanned)
            received_qty = float(item.weight or 0)  # Quantity received now
            source_warehouse = "Transit - SPP INDIA"  # The warehouse the item came from
            target_warehouse = "U1-Store - SPP INDIA"  # The target warehouse for the item

            # Process the stock based on received and DC quantities
            self.process_stock_entry(item_code, dc_qty, received_qty, source_warehouse, target_warehouse)

    def process_stock_entry(self, item_code, dc_qty, received_qty, source_warehouse, target_warehouse):
        # Define the 50g tolerance (in kilograms)
        tolerance = 0.05  # Assuming quantities are in kg

        # Calculate the difference in quantities
        difference = received_qty - dc_qty

        # Check if the difference exceeds the tolerance
        if abs(difference) > tolerance:
            # Create a Stock Reconciliation entry to adjust the stock
            self.create_stock_reconciliation(item_code, difference, source_warehouse,purpose = 'Stock Reconciliation')

            # Transfer item to the target warehouse after reconciliation
            self.create_material_transfer(item_code, received_qty, source_warehouse, target_warehouse)

        else:
            # If within tolerance, create a Material Transfer entry for the DC quantity
            self.create_material_transfer(item_code, received_qty, source_warehouse, target_warehouse)

    def create_stock_reconciliation(self, item_code, qty, warehouse,purpose):
        # Create a Stock Reconciliation entry to adjust the stock in the source warehouse
        reconciliation_entry = frappe.new_doc('Stock Reconciliation')
        reconciliation_entry.purpose = purpose
        reconciliation_entry.append('items', {
            'item_code': item_code,
            'warehouse': warehouse,
            'qty': qty
        })
        reconciliation_entry.save()
        reconciliation_entry.submit()

    def create_material_transfer(self, item_code, qty, source_warehouse, target_warehouse):
        # Create a Stock Entry for Material Transfer
        stock_entry = frappe.new_doc('Stock Entry')
        stock_entry.stock_entry_type = 'Material Transfer'
        stock_entry.append('items', {
            'item_code': item_code,
            'qty': qty,
            's_warehouse': source_warehouse,
            't_warehouse': target_warehouse
        })
        stock_entry.save()
        stock_entry.submit()
    

@frappe.whitelist(allow_guest= True)
def get_erp_batch_number(dc_no, spp_batch_number):
    
    delivery_note_doc = frappe.get_doc("Delivery Note",dc_no)
    # Initialize a list to hold the matching items
    matching_items = []
    
    if delivery_note_doc:
        # Loop through the items in the Delivery Note
        for item in delivery_note_doc.items:
            # Check if the item has the matching spp_batch_number
            if item.spp_batch_no == spp_batch_number:
                
                
                # Fetch the UOM conversion factor from UOM Conversion Detail table
                conversion_factor = frappe.db.get_value(
                    'UOM Conversion Detail',
                    {'parent': item.item_code, 'uom': "Kg"},
                    'conversion_factor'
                )

                # If a conversion factor is found, calculate the actual quantity
                if conversion_factor:
                    actual_qty = item.qty * conversion_factor
                else:
                    actual_qty = item.qty  # Default to item qty if no conversion factor is found
            
                # Collect item_code, calculated qty, and batch_no
                matching_items.append({
                    'item_code': item.item_code,
                    'qty': item.qty,  # Adjusted quantity based on UOM conversion
                    'batch_no': item.batch_no,
                    'qty_kg':item.qty * conversion_factor
                })
    
    return matching_items if matching_items else None

