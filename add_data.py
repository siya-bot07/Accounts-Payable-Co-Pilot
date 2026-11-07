from app import app, db, PurchaseOrder

with app.app_context():
    # This creates the empty database file (erp.db)
    db.create_all()
    
    # Check if the PO already exists to avoid duplicates
    existing_po = PurchaseOrder.query.filter_by(po_number="PO-77321").first()
    
    if not existing_po:
        # Create a new record
        new_po = PurchaseOrder(
            po_number="PO-77321",
            vendor="Contoso Tech Solutions",
            approved_amount=200.00
        )
        
        # Save it to the database
        db.session.add(new_po)
        db.session.commit()
        print("Successfully saved PO-77321 to the database!")
    else:
        print("PO-77321 is already in the database.")