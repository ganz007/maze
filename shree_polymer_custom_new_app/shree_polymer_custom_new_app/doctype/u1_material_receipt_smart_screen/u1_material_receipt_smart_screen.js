frappe.ui.form.on('U1 Material Receipt Smart Screen', {
    onload: function(frm) {
        // Set filters for 'DC No.' field linked to 'Delivery Note'
        frm.set_query('dc_no', function() {
            return {
                filters: {
                    customer: 'Shree Polymer Products - Factory 2',
                    set_warehouse: 'Transit - SPP INDIA'
                }
            };
        });

        // Set current date and time
        frm.set_value('date', frappe.datetime.now_date());
        frm.set_value('time', frappe.datetime.now_time());
    },

    scan_lot_barcode: function(frm) {
        const scan_lot_barcode = frm.doc.scan_lot_barcode;

        if (scan_lot_barcode) {
            const new_row = frm.add_child('items');
            new_row.lot_no = scan_lot_barcode;

            const dc_no = frm.doc.dc_no;

            if (new_row.lot_no && dc_no) {
                fetch_batch_details(frm, new_row, dc_no); // Pass frm to the function
            } else {
                frappe.msgprint(__('DC No is missing.'));
            }

            // Clear the scan_lot_barcode field after adding the row
            frm.set_value('scan_lot_barcode', '');
            frm.refresh_field('items'); // Refresh to reflect changes
        }
    }
});

// Handle the item level events
frappe.ui.form.on('U1 Material Receipt Smart Screen Item', {
    lot_no: function(frm, cdt, cdn) {
        const child = locals[cdt][cdn];
        const scanned_lot = child.lot_no;
        const dc_no = frm.doc.dc_no;

        if (scanned_lot) {
            fetch_batch_details(frm, child, dc_no); // Pass frm to the function
        }
    },

    weight: function(frm, cdt, cdn) {
        const child = locals[cdt][cdn];

        if (child.item_code) {
            frappe.db.get_doc("Item", child.item_code)
                .then(item_doc => update_child_status(frm, child, item_doc)) // Pass frm to the function
                .catch(error => console.error("Error fetching item:", error));
        }
    }
});

// Function to fetch batch details
function fetch_batch_details(frm, child, dc_no) { // Added frm as a parameter
    const lot_no = child.lot_no;

    frappe.call({
        method: 'shree_polymer_custom_new_app.shree_polymer_custom_new_app.doctype.u1_material_receipt_smart_screen.u1_material_receipt_smart_screen.get_erp_batch_number',
        args: {
            dc_no: dc_no,
            spp_batch_number: lot_no
        },
        callback: function(response) {
            if (response.message) {
                child.item_code = response.message[0].item_code;
                child.qty_nos = response.message[0].qty;
                child.qty_kg = response.message[0].qty_kg;
                frm.refresh_field('items'); // Refresh the child table
            } else {
                frappe.msgprint(__('No batch found for the scanned lot number.'));
            }
        }
    });
}

// Function to update child status based on item details
function update_child_status(frm, child, item_doc) { // Added frm as a parameter
    if (item_doc.uoms) {
        let conversion_factor = item_doc.uoms.find(uom => uom.uom === 'Kg')?.conversion_factor || 1;
        const received_weight = child.weight || 0;
        const qty_nos = Math.round(child.qty_nos * conversion_factor);  // Calculate Qty in Nos
        const status = update_status(received_weight, qty_nos); // Update status
        child.status = status; // Update status on child
        frm.refresh_field('items'); // Refresh the child table
    } else {
        console.log("No UOMs found for this item.");
    }
}

// Function to update status based on received quantity
function update_status(received_qty, dc_qty) {
    const tolerance = 0.05;  // Assuming the weight is in kg
    const variation = received_qty - dc_qty;
    const variation_abs = Math.abs(variation);  // Absolute variation

    if (variation_abs <= tolerance) {
        return 'OK';  // Within tolerance
    } else if (variation > tolerance) {
        return 'EXCESS';  // Received more than expected
    } else {
        return 'SHORT';  // Received less than expected
    }
}