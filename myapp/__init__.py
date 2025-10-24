from flask import Flask, request, jsonify

app = Flask(__name__)

@app.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    # Validate empty fields
    if not username or not password:
        return jsonify(error="Missing username or password."), 400

    # Correct credentials
    if username == "admin" and password == "1234":
        return jsonify(message="Access granted ✅"), 200

    # Incorrect credentials
    return jsonify(error="Invalid credentials ❌"), 401


if __name__ == "__main__":
    app.run(debug=True)



