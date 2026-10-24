from pyrogram import Client

# -------------------------------------------------------------
# এখানে আপনার API_ID এবং API_HASH সরাসরি বসানো আছে
# -------------------------------------------------------------
API_ID = 35999298
API_HASH = "69fd352462046b14e90b5e1f0fa66425"

print("\n--- Assistant String Session Generator ---\n")

with Client(name="assistant_session", api_id=API_ID, api_hash=API_HASH, in_memory=True) as app:
    session = app.export_session_string()
    print("\n\n✅ আপনার নতুন STRING_SESSION তৈরি হয়ে গেছে (এটি কপি করে নিন):\n")
    print(session)
    print("\n" + "=" * 50 + "\n")