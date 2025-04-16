import zipfile

with zipfile.ZipFile("BrandStrategyAgent.zip", "r") as zip_ref:
    zip_ref.extractall()
print("✅ Unzipped successfully!")
