#!/usr/bin/env python3
"""
Simple script to list experiences from Weaviate database
Usage: python simple_list_experiences.py [--limit N] [--company "Company Name"]

This script connects directly to Weaviate without using any abstractions
and lists all experiences stored in the Experience collection.
"""

import argparse
import json
import os
import sys
from typing import Optional, List, Dict, Any

try:
    import weaviate
    from weaviate.classes.query import Filter
except ImportError:
    print("Error: weaviate-client is not installed.")
    print("Please install it with: pip install weaviate-client")
    sys.exit(1)


def connect_to_weaviate(host: str = "localhost", port: int = 8080) -> weaviate.WeaviateClient:
    """
    Connect to local Weaviate instance
    
    Args:
        host: Weaviate host (default: localhost)
        port: Weaviate port (default: 8080)
        
    Returns:
        Connected Weaviate client
        
    Raises:
        Exception: If connection fails
    """
    try:
        # Connect to local Weaviate instance
        client = weaviate.connect_to_local(
            host=host,
            port=port,
            headers={
                "X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY", "")
            }
        )
        
        # Test connection
        if not client.is_ready():
            raise Exception("Weaviate client not ready")
            
        print(f"✅ Connected to Weaviate at {host}:{port}")
        return client
        
    except Exception as e:
        print(f"❌ Failed to connect to Weaviate: {e}")
        print("Make sure Weaviate is running locally on port 8080")
        print("You can start it with: docker-compose up -d")
        sys.exit(1)


def list_experiences(client: weaviate.WeaviateClient, 
                    limit: Optional[int] = None,
                    company_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List experiences from Weaviate Experience collection
    
    Args:
        client: Connected Weaviate client
        limit: Maximum number of experiences to return
        company_filter: Filter by company name
        
    Returns:
        List of experience dictionaries
        
    Raises:
        Exception: If query fails
    """
    try:
        # Get the Experience collection
        collection = client.collections.get("Experience")
        
        # Build query with limit
        query = collection.query.fetch_objects(
            limit=limit or 100
        )
        
        # Apply company filter if provided
        if company_filter:
            query = query.where(
                Filter.by_property("company_name").equal(company_filter)
            )
        
        # Execute query
        response = query
        
        # Convert results to dictionaries
        experiences = []
        for obj in response.objects:
            # Get all properties from the object
            exp_dict = dict(obj.properties)
            # Add the UUID as id
            exp_dict['id'] = str(obj.uuid)
            experiences.append(exp_dict)
        
        return experiences
        
    except Exception as e:
        print(f"❌ Failed to list experiences: {e}")
        print("Make sure the Experience collection exists in Weaviate")
        sys.exit(1)


def get_experience_by_id(client: weaviate.WeaviateClient, experience_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific experience by ID
    
    Args:
        client: Connected Weaviate client
        experience_id: Unique identifier of the experience
        
    Returns:
        Experience dictionary if found, None otherwise
        
    Raises:
        Exception: If query fails
    """
    try:
        # Get the Experience collection
        collection = client.collections.get("Experience")
        
        # Get experience by ID using query interface
        result = collection.query.fetch_object_by_id(experience_id)
        
        if not result:
            return None
        
        # Convert to dictionary
        exp_dict = dict(result.properties)
        exp_dict['id'] = str(result.uuid)
        
        return exp_dict
        
    except Exception as e:
        print(f"❌ Failed to retrieve experience {experience_id}: {e}")
        print("Make sure the Experience collection exists in Weaviate")
        sys.exit(1)


def delete_experience_by_id(client: weaviate.WeaviateClient, experience_id: str) -> bool:
    """
    Delete a specific experience by ID
    
    Args:
        client: Connected Weaviate client
        experience_id: Unique identifier of the experience
        
    Returns:
        True if deletion was successful, False otherwise
        
    Raises:
        Exception: If deletion fails
    """
    try:
        # Get the Experience collection
        collection = client.collections.get("Experience")
        
        # Delete the experience
        collection.data.delete_by_id(experience_id)
        
        print(f"✅ Successfully deleted experience: {experience_id}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to delete experience {experience_id}: {e}")
        print("Make sure the Experience collection exists in Weaviate")
        return False


def format_experience(exp: Dict[str, Any], index: int) -> str:
    """
    Format a single experience for display
    
    Args:
        exp: Experience dictionary
        index: Experience number for display
        
    Returns:
        Formatted string representation
    """
    company = exp.get('company_name', 'Unknown Company')
    skills = exp.get('skills', [])
    categories = exp.get('categories', [])
    text = exp.get('original_text', '')
    created_date = exp.get('created_date', '')
    
    # Handle datetime objects for created_date
    if hasattr(created_date, 'strftime'):
        # It's a datetime object
        created_str = created_date.strftime('%Y-%m-%d')
    elif isinstance(created_date, str) and created_date:
        # It's a string, take first 10 characters
        created_str = created_date[:10]
    else:
        # It's empty or None
        created_str = 'Unknown'
    
    # Truncate text for preview
    text_preview = text[:150] + "..." if len(text) > 150 else text
    
    result = f"""
{index}. {company}
   ID: {exp.get('id', 'N/A')}
   Skills: {', '.join(skills[:5]) if skills else 'None'}
   Categories: {', '.join(categories) if categories else 'None'}
   Created: {created_str}
   Text: {text_preview}
"""
    return result


def main():
    """
    Main function to parse arguments and handle operations
    """
    parser = argparse.ArgumentParser(
        description="Manage experiences in Weaviate database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List experiences
  python simple_list_experiences.py
  python simple_list_experiences.py --limit 5
  python simple_list_experiences.py --company "TechCorp"
  
  # Get specific experience
  python simple_list_experiences.py --get-id "12345-abcde-67890"
  
  # Delete experience
  python simple_list_experiences.py --delete-id "12345-abcde-67890"
  python simple_list_experiences.py --delete-id "12345-abcde-67890" --no-confirm
        """
    )
    
    # Operation mode arguments
    operation_group = parser.add_mutually_exclusive_group()
    operation_group.add_argument(
        '--get-id',
        type=str,
        help='Get a specific experience by ID'
    )
    operation_group.add_argument(
        '--delete-id',
        type=str,
        help='Delete a specific experience by ID'
    )
    
    # List operation arguments
    parser.add_argument(
        '--limit', 
        type=int, 
        help='Maximum number of experiences to return (default: 100)'
    )
    
    parser.add_argument(
        '--company', 
        type=str, 
        help='Filter experiences by company name'
    )
    
    # Output format
    parser.add_argument(
        '--json', 
        action='store_true', 
        help='Output results in JSON format'
    )
    
    # Delete confirmation
    parser.add_argument(
        '--no-confirm',
        action='store_true',
        help='Skip confirmation prompt for delete operations'
    )
    
    # Connection arguments
    parser.add_argument(
        '--host', 
        type=str, 
        default='localhost', 
        help='Weaviate host (default: localhost)'
    )
    
    parser.add_argument(
        '--port', 
        type=int, 
        default=8080, 
        help='Weaviate port (default: 8080)'
    )
    
    args = parser.parse_args()
    
    # Connect to Weaviate
    client = connect_to_weaviate(args.host, args.port)
    
    try:
        # Handle get operation
        if args.get_id:
            experience = get_experience_by_id(client, args.get_id)
            
            if not experience:
                print(f"📭 No experience found with ID: {args.get_id}")
                return
            
            # Display result
            if args.json:
                print(json.dumps(experience, indent=2, default=str))
            else:
                print(f"\n📋 Found experience with ID: {args.get_id}")
                print("=" * 60)
                print(format_experience(experience, 1))
            return
        
        # Handle delete operation
        if args.delete_id:
            # Check if experience exists first
            experience = get_experience_by_id(client, args.delete_id)
            
            if not experience:
                print(f"📭 No experience found with ID: {args.delete_id}")
                return
            
            # Show what will be deleted
            print(f"\n🗑️  About to delete experience:")
            print("=" * 60)
            print(format_experience(experience, 1))
            
            # Confirm deletion if required
            if not args.no_confirm:
                confirm = input("\nAre you sure you want to delete this experience? (y/N): ")
                if confirm.lower() not in ['y', 'yes']:
                    print("❌ Deletion cancelled")
                    return
            
            # Perform deletion
            success = delete_experience_by_id(client, args.delete_id)
            if not success:
                sys.exit(1)
            return
        
        # Default: List experiences
        experiences = list_experiences(
            client, 
            limit=args.limit, 
            company_filter=args.company
        )
        
        if not experiences:
            print("📭 No experiences found")
            if args.company:
                print(f"   (with company filter: '{args.company}')")
            return
        
        # Display results
        if args.json:
            # JSON output
            print(json.dumps(experiences, indent=2, default=str))
        else:
            # Human-readable output
            print(f"\n📋 Found {len(experiences)} experience(s)")
            if args.company:
                print(f"   (filtered by company: '{args.company}')")
            print("=" * 60)
            
            for i, exp in enumerate(experiences, 1):
                print(format_experience(exp, i))
                if i < len(experiences):
                    print("-" * 40)
    
    finally:
        # Always close the client connection
        client.close()
        print("\n🔌 Disconnected from Weaviate")


if __name__ == "__main__":
    main()