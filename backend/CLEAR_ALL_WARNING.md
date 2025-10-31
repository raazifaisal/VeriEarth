# Data Management - Clear All Behavior

## ⚠️ **IMPORTANT: Clear All Facilities**

When you click **"Clear All facilities"**, it will delete **EVERYTHING** related to your organization in the database:

### **What Gets Deleted:**

1. **🏭 All Facilities** (your warehouses, distribution centers, etc.)
2. **🌍 All Environmental Data** (EO data, AQI scores, pollution measurements)
3. **🚛 All Routes** (transportation routes between facilities)
4. **📦 All Shipments** (shipment records and tracking data)
5. **🛒 All Purchase Orders** (orders from suppliers)
6. **📊 All Analytics Data** (any calculated metrics, reports)

### **What Stays:**

- ✅ **Organizations** (your company info)
- ✅ **Users** (login accounts)
- ✅ **Suppliers** (supplier information)
- ✅ **Products** (product catalog)

### **Why This Happens:**

The database has foreign key relationships:
```
Facilities → Routes → Shipments
Facilities → Purchase Orders
Facilities → Environmental Data
```

To delete facilities, we must delete all dependent records first to maintain data integrity.

### **Use Cases:**

- **🧪 Testing**: Clear all data to start fresh with new test data
- **🔄 Reset**: Remove all imported data to re-import with different settings
- **🗑️ Cleanup**: Remove all data before switching organizations

### **Alternative Actions:**

Instead of "Clear All", you can:
- **Edit individual records** using the Edit button
- **Delete specific records** using the Delete button
- **Import new data** without clearing (it will add to existing data)

### **Confirmation Required:**

The system will ask you to type **"facilities"** to confirm this destructive action, similar to AWS/GCP deletion confirmations.

---

## 🔧 **Technical Details**

### **Deletion Order:**
1. `facility_environmental_data` (EO data)
2. `shipments` (depends on routes)
3. `routes` (depends on facilities)
4. `purchase_orders` (depends on facilities)
5. `facilities` (main records)

### **Error Handling:**
If deletion fails due to foreign key constraints, you'll get a user-friendly error message explaining which records are preventing deletion.

### **Recovery:**
Once cleared, data cannot be recovered unless you have backups. Make sure you want to proceed!

---

## 💡 **Best Practices**

1. **📋 Export Data First**: If you need the data later, export it before clearing
2. **🧪 Test Environment**: Use this feature in development/testing environments
3. **📊 Backup**: Consider backing up important data before bulk operations
4. **🔄 Incremental**: For production, prefer editing individual records over bulk clearing

---

## ✅ **Summary**

**"Clear All facilities"** = **Nuclear option** that removes ALL supply chain data for your organization.

Use with caution! 🚨
