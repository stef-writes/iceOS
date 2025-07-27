"""Facebook Marketplace Seller - Automated listing and sales management system.

This package provides a complete workflow for managing Facebook Marketplace listings,
including inventory analysis, pricing optimization, listing creation, and customer communication.

Usage:
    from use_cases.RivaRidge.FB_Marketplace_Seller import FBMSeller
    
    seller = FBMSeller(config={
        "marketplace": "facebook",
        "location": "Seattle, WA",
        "category": "Electronics"
    })
    
    results = await seller.run(inventory_data)
"""

from .FBMSeller import FBMSeller

__all__ = [
    "FBMSeller"
] 