# Script para eliminar todos los servicios de prueba
# Elimina servicios que empiezan por "test_" en organization "services"

import time
import getpass
from ndp_ep import APIClient

def cleanup_test_services():
    """
    Clean up all test services that start with 'test_' in 'services' org.
    """
    
    # Configuration
    API_BASE_URL = "http://localhost:8003"
    PREFIX = "test_"
    SERVICES_ORG = "services"
    
    print("🧹 TEST SERVICES CLEANUP SCRIPT")
    print("=" * 50)
    print(f"Target: Services starting with '{PREFIX}' in '{SERVICES_ORG}' org")
    print(f"API: {API_BASE_URL}")
    
    # Get credentials
    print("\n🔐 Authentication Required")
    api_token = getpass.getpass("Enter API Token: ")
    
    if not api_token.strip():
        print("❌ No token provided. Exiting.")
        return
    
    # Initialize client
    try:
        client = APIClient(base_url=API_BASE_URL, token=api_token)
        print("✅ Client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        return
    
    # Search for test services
    print(f"\n🔍 Searching for test services...")
    try:
        # Search for services in the services organization
        search_results = client.advanced_search({
            "owner_org":"services",
            "server": "local"
        })
        print(f"📊 Found {len(search_results)} total services in 'services' org")
        # Filter services that start with our prefix
        test_services = [
            service for service in search_results 
            if service.get("name", "").startswith(PREFIX + "service_")
        ]
        
        print(f"📊 Found {len(test_services)} test services to delete")
        
        if len(test_services) == 0:
            print("✅ No test services found. Nothing to clean up!")
            return
        
        # Show services to be deleted
        print(f"\n📋 Services to be deleted:")
        for i, service in enumerate(test_services[:10], 1):
            name = service.get("name", "Unknown")
            service_id = service.get("id", "No ID")
            print(f"   {i:3d}. {name} (ID: {service_id})")
        
        if len(test_services) > 10:
            print(f"   ... and {len(test_services) - 10} more")
            
    except Exception as e:
        print(f"❌ Failed to search for services: {e}")
        return
    
    # Confirmation
    print(f"\n⚠️  WARNING: About to delete {len(test_services)} services!")
    confirmation = input("Type 'DELETE' to proceed: ").strip()
    
    if confirmation != 'DELETE':
        print("🚫 Operation cancelled by user")
        return
    
    # Delete services
    print(f"\n🗑️  Deleting {len(test_services)} test services...")
    print("=" * 40)
    
    deleted_count = 0
    failed_count = 0
    
    for i, service in enumerate(test_services, 1):
        service_name = service.get("name", f"service_{i}")
        
        try:
            # Delete by name (most reliable)
            client.delete_resource_by_name(service_name, server="local")
            deleted_count += 1
            
            timestamp = time.strftime("%H:%M:%S")
            print(f"✅ [{timestamp}] Deleted: {service_name}")
            
        except Exception as e:
            failed_count += 1
            timestamp = time.strftime("%H:%M:%S")
            print(f"❌ [{timestamp}] Failed to delete {service_name}: {e}")
        
        # Progress indicator
        if i % 10 == 0 or i == len(test_services):
            percentage = (i / len(test_services)) * 100
            print(f"📈 Progress: {i}/{len(test_services)} ({percentage:.1f}%)")
        
        # Small delay to avoid overwhelming the API
        time.sleep(0.2)
    
    # Final summary
    print(f"\n📊 CLEANUP SUMMARY")
    print("=" * 30)
    print(f"✅ Successfully deleted: {deleted_count}")
    print(f"❌ Failed to delete: {failed_count}")
    print(f"📦 Total processed: {len(test_services)}")
    
    if failed_count == 0:
        print(f"\n🎉 All test services cleaned up successfully!")
    else:
        print(f"\n⚠️  {failed_count} services could not be deleted")
        print(f"   Manual cleanup may be required")
    
    # Verification
    print(f"\n🔍 Verifying cleanup...")
    try:
        verify_results = client.advanced_search({
            "search_term": PREFIX.rstrip("_"),
            "filter_list": [f"owner_org:{SERVICES_ORG}"],
            "server": "local"
        })
        
        remaining_services = [
            s for s in verify_results 
            if s.get("name", "").startswith(PREFIX + "service_")
        ]
        
        print(f"📊 Remaining test services: {len(remaining_services)}")
        
        if len(remaining_services) == 0:
            print("✅ Cleanup verification: SUCCESS - No test services remain")
        else:
            print(f"⚠️  Cleanup verification: {len(remaining_services)} services still exist")
            
    except Exception as e:
        print(f"❌ Verification failed: {e}")


if __name__ == "__main__":
    cleanup_test_services()