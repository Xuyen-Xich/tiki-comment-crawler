"""
Category service for managing category data.
"""
import pandas as pd
from typing import List, Dict, Optional
from core.logger import logger
from core.storage import DataStorage
from models import CategoryModel
from config.settings import settings


class CategoryService:
    """Manages category data operations."""

    @staticmethod
    def categories_to_dataframe(categories: List[CategoryModel]) -> pd.DataFrame:
        """
        Convert category models to DataFrame.
        
        Args:
            categories: List of category models
            
        Returns:
            DataFrame with category data
        """
        logger.info(f"Converting {len(categories)} categories to DataFrame")
        
        data = [cat.dict() for cat in categories]
        df = pd.DataFrame(data)
        
        logger.info(f"Created DataFrame with shape: {df.shape}")
        return df

    @staticmethod
    def save_categories(
        categories: List[CategoryModel],
        output_dir: str,
        filename: str = "tiki_categories",
        formats: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """
        Save categories to files.
        
        Args:
            categories: List of category models
            output_dir: Output directory
            filename: Output filename
            formats: Export formats
            
        Returns:
            Export results
        """
        if formats is None:
            formats = [settings.MENU_OUTPUT_FORMAT]
        
        logger.info(f"Saving {len(categories)} categories")
        
        df = CategoryService.categories_to_dataframe(categories)
        
        results = DataStorage.export_dataframe(
            df,
            output_dir,
            filename,
            formats,
        )
        
        logger.info(f"Categories saved: {results}")
        return results

    @staticmethod
    def load_categories(file_path: str) -> List[CategoryModel]:
        """
        Load categories from file.
        
        Args:
            file_path: Path to category file
            
        Returns:
            List of category models
        """
        logger.info(f"Loading categories from {file_path}")
        
        df = DataStorage.load_dataframe(file_path)
        
        categories = [
            CategoryModel(**row.to_dict())
            for _, row in df.iterrows()
        ]
        
        logger.info(f"Loaded {len(categories)} categories")
        return categories

    @staticmethod
    def get_unique_categories(
        categories: List[CategoryModel],
    ) -> List[CategoryModel]:
        """
        Get unique categories by category_id.
        
        Args:
            categories: List of categories
            
        Returns:
            List of unique categories
        """
        logger.info(f"Deduplicating {len(categories)} categories")
        
        seen = set()
        unique = []
        
        for cat in categories:
            if cat.category_id and cat.category_id not in seen:
                seen.add(cat.category_id)
                unique.append(cat)
        
        logger.info(f"Unique categories: {len(unique)}")
        return unique

    @staticmethod
    def get_categories_by_level(
        categories: List[CategoryModel],
        level: int = 1,
    ) -> List[CategoryModel]:
        """
        Get categories by level (1, 2, or 3).
        
        Args:
            categories: List of categories
            level: Category level (1-3)
            
        Returns:
            Filtered categories
        """
        if level == 1:
            filtered = [c for c in categories if c.lv1_name and not c.lv2_name]
        elif level == 2:
            filtered = [c for c in categories if c.lv2_name and not c.lv3_name]
        elif level == 3:
            filtered = [c for c in categories if c.lv3_name]
        else:
            filtered = categories
        
        logger.info(f"Level {level}: {len(filtered)} categories")
        return filtered
