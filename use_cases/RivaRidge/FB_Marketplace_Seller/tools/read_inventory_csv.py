"""Read and validate CSV inventory tool for FB Marketplace."""

import csv
from pathlib import Path
from typing import Dict, Any
from ice_sdk.tools.base import ToolBase


class ReadInventoryCSVTool(ToolBase):
    """Reads and validates inventory CSV file."""
    
    name: str = "read_inventory_csv"
    description: str = "Reads CSV inventory file and validates product data"
    
    async def execute(self, input_data: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given inputs."""
        # Merge input_data with kwargs for flexibility
        merged_inputs = {**(input_data or {}), **kwargs}
        return await self._execute_impl(**merged_inputs)
    
    async def _execute_impl(self, csv_file: str, **kwargs) -> Dict[str, Any]:
        """Read and parse the inventory CSV file."""
        
        file_path = Path(csv_file)
        if not file_path.exists():
            return {
                "success": False,
                "error": f"CSV file not found: {csv_file}",
                "items": []
            }
        
        items = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Auto-detect delimiter
                sample = f.read(1024)
                f.seek(0)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                
                reader = csv.DictReader(f, delimiter=delimiter)
                
                for row_num, row in enumerate(reader, start=2):
                    # Clean and validate each row
                    item = self._clean_item(row, row_num)
                    if item:
                        items.append(item)
            
            return {
                "success": True,
                "items_imported": len(items),
                "clean_items": items,
                "source_file": str(file_path)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error reading CSV: {str(e)}",
                "items": []
            }
    
    def _clean_item(self, row: Dict[str, str], row_num: int) -> Dict[str, Any]:
        """Clean and standardize a single inventory item."""
        
        # Required fields with flexible column name matching
        sku = row.get('SKU', '').strip() or row.get('Item ID', '').strip()
        name = row.get('Product Name', '').strip() or row.get('Name', '').strip()
        
        if not sku or not name:
            print(f"⚠️  Row {row_num}: Missing SKU or Product Name, skipping")
            return None
        
        # Clean and convert data types
        try:
            price = float(row.get('Price', '0').replace('$', '').replace(',', ''))
        except ValueError:
            price = 0.0
        
        try:
            # Try multiple possible column names for quantity
            qty_value = row.get('Quantity', '') or row.get('In Stock (Qty)', '') or row.get('Qty', '') or '0'
            quantity = int(qty_value)
        except ValueError:
            quantity = 0
        
        item = {
            "sku": sku,
            "name": name,
            "description": row.get('Description', '').strip(),
            "price": price,
            "quantity": quantity,
            "category": row.get('Category', '').strip(),
            "condition": row.get('Condition', 'Used').strip(),
            "brand": row.get('Brand', '').strip(),
            "location": row.get('Location', '').strip(),
            "weight": row.get('Weight', '').strip(),
            "dimensions": row.get('Dimensions', '').strip(),
            "source_row": row_num
        }
        
        return item 