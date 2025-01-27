from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os
import pandas as pd

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define database model
class DataEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    num = db.Column(db.Integer, nullable=False)
    product = db.Column(db.String(200), nullable=False)
    title = db.Column(db.String(500), nullable=True)
    document_type = db.Column(db.String(50), nullable=True)
    reference_number = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(50), nullable=True)
    number_of_pages = db.Column(db.Integer, nullable=True)
    date_of_publication = db.Column(db.DateTime, nullable=True)
    price = db.Column(db.String(50), nullable=True)
    date_assigned = db.Column(db.DateTime, nullable=True)
    author_contact = db.Column(db.String(200), nullable=True)
    purpose = db.Column(db.String(50), nullable=True)
    va_team_member = db.Column(db.String(200), nullable=True)

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    print("Accessed upload route")
    if request.method == 'POST':
        file = request.files['file']
        if file:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            print("File uploaded to:", filepath)

            # Load the Excel file into a DataFrame
            data = pd.read_excel(filepath)
            print("Original DataFrame:\n", data)

            # Reverse the DataFrame to insert rows from the bottom
            data = data.iloc[::-1]
            print("Reversed DataFrame:\n", data)

            def parse_date(value):
                """Safely parse date values, handling pandas NaT and datetime.datetime."""
                if pd.notna(value):
                    return pd.to_datetime(value).to_pydatetime()
                return None

            for _, row in data.iterrows():
                print(f"Processing row: {row}")  # Debug row data

                # Insert data exactly as it appears in the Excel file
                entry = DataEntry(
                    num=row.get('Num', 0),
                    product=row.get('Product', "Unknown"),
                    title=row.get('Title', "Untitled") if pd.notna(row.get('Title', None)) else "Untitled",
                    document_type=row.get('Document Type', "Unknown"),
                    reference_number=row.get('Reference Number', "N/A"),
                    status=row.get('Status', "Unknown"),
                    number_of_pages=int(row.get('Number of Pages', 0)) if pd.notna(row.get('Number of Pages', None)) else 0,
                    date_of_publication=parse_date(row.get('Date of Publication', None)),
                    price=row.get('Price', "0"),
                    date_assigned=parse_date(row.get('Date Assigned', None)),
                    author_contact=row.get('Author/Contact', "Unknown"),
                    purpose=row.get('Purpose', "Unknown") if pd.notna(row.get('Purpose', None)) else "Unknown",
                    va_team_member=row.get('VA Team Member', "Unknown")
                )
                db.session.add(entry)
            db.session.commit()
            print("Data committed to database")
            return redirect(url_for('view_data'))

    return render_template('upload.html')

@app.route('/view')
def view_data():
    # Fetch data ordered by ID in descending order
    data = DataEntry.query.order_by(DataEntry.id.desc()).all()
    
    # Format dates and reorder columns for display
    formatted_data = [
        {
            'id': entry.id,
            'product': entry.product,
            'title': entry.title,
            'document_type': entry.document_type,
            'reference_number': entry.reference_number,
            'status': entry.status,
            'number_of_pages': entry.number_of_pages,
            'date_of_publication': entry.date_of_publication.strftime('%Y-%m-%d') if entry.date_of_publication else '',
            'price': entry.price,
            'date_assigned': entry.date_assigned.strftime('%Y-%m-%d') if entry.date_assigned else '',
            'author_contact': entry.author_contact,
            'purpose': entry.purpose,
            'num': entry.num,
            'va_team_member': entry.va_team_member,
        }
        for entry in data
    ]
    
    print("Data passed to view (latest first):", formatted_data)
    return render_template('table.html', data=formatted_data)

# Delete all
@app.route('/delete_all', methods=['POST'])
def delete_all():
    """
    Deletes all entries from the DataEntry table and redirects back to the view page.
    """
    print("Deleting all entries from the database.")
    try:
        db.session.query(DataEntry).delete()  # Deletes all rows in the table
        db.session.commit()
        print("All entries deleted successfully.")
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting entries: {e}")
    return redirect(url_for('view_data'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_entry(id):
    entry = DataEntry.query.get_or_404(id)
    if request.method == 'POST':
        # Update entry with form data
        entry.product = request.form.get('product', entry.product)
        entry.title = request.form.get('title', entry.title)
        entry.document_type = request.form.get('document_type', entry.document_type)
        entry.reference_number = request.form.get('reference_number', entry.reference_number)
        entry.status = request.form.get('status', entry.status)
        entry.number_of_pages = int(request.form.get('number_of_pages', entry.number_of_pages))
        entry.date_of_publication = pd.to_datetime(request.form.get('date_of_publication', None)).to_pydatetime() if request.form.get('date_of_publication') else entry.date_of_publication
        entry.price = request.form.get('price', entry.price)
        entry.date_assigned = pd.to_datetime(request.form.get('date_assigned', None)).to_pydatetime() if request.form.get('date_of_assigned') else entry.date_assigned
        entry.author_contact = request.form.get('author_contact', entry.author_contact)
        entry.purpose = request.form.get('purpose', entry.purpose)
        entry.num = int(request.form.get('num', entry.num))
        entry.va_team_member = request.form.get('va_team_member', entry.va_team_member)

        # Commit changes
        db.session.commit()
        print("Entry updated:", entry)
        return redirect(url_for('view_data'))

    return render_template('edit_entry.html', entry=entry)

@app.route('/add_entry', methods=['GET', 'POST'])
def add_entry():
    if request.method == 'POST':
        # Auto-increment 'num'
        latest_entry = db.session.query(DataEntry).order_by(DataEntry.num.desc()).first()
        num = (latest_entry.num + 1) if latest_entry else 1  # Start with 1 if no entries exist

        # Update only the last 4 digits of the reference_number
        base_reference_number = request.form.get('reference_number', "REF-0000")[:-4]
        reference_number = f"{base_reference_number}{str(num).zfill(4)}"

        # Get other form data
        product = request.form.get('product', "Unknown")
        title = request.form.get('title', "Untitled")
        document_type = request.form.get('document_type', "Unknown")
        status = request.form.get('status', "Unknown")
        number_of_pages = int(request.form.get('number_of_pages', 0))
        date_of_publication = pd.to_datetime(request.form.get('date_of_publication', None)).to_pydatetime() if request.form.get('date_of_publication') else None
        price = request.form.get('price', "0")
        date_assigned = pd.to_datetime(request.form.get('date_assigned', None)).to_pydatetime() if request.form.get('date_assigned') else None
        author_contact = request.form.get('author_contact', "Unknown")
        purpose = request.form.get('purpose', "Unknown")
        va_team_member = request.form.get('va_team_member', "Unknown")

        # Create new entry
        entry = DataEntry(
            num=num,
            product=product,
            title=title,
            document_type=document_type,
            reference_number=reference_number,
            status=status,
            number_of_pages=number_of_pages,
            date_of_publication=date_of_publication,
            price=price,
            date_assigned=date_assigned,
            author_contact=author_contact,
            purpose=purpose,
            va_team_member=va_team_member
        )
        db.session.add(entry)
        db.session.commit()
        print("New entry added:", entry)
        return redirect(url_for('view_data'))

    return render_template('add_entry.html')

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    with app.app_context():
        db.create_all()
    print("Starting Flask server")
    app.run(debug=True)
