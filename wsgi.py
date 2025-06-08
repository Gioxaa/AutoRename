from app import app, init_app

# Initialize the app for production
init_app(app)

# WSGI entry point
if __name__ == "__main__":
    app.run() 