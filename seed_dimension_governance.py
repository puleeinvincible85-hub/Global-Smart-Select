from src.database import (
    initialize_database,
    update_dimension_governance,
)


def seed():
    """
    Seed initial dimension governance rules.
    """

    initialize_database()


    # -----------------------------------------------------
    # GOVERNED DIMENSIONS
    # -----------------------------------------------------

    update_dimension_governance(
        dimension_name="country",
        display_name="Country",
        governed=True,
        taxonomy_category="regions",
        data_type="dimension",
    )


    update_dimension_governance(
        dimension_name="region",
        display_name="Region",
        governed=True,
        taxonomy_category="regions",
        data_type="dimension",
    )


    update_dimension_governance(
        dimension_name="market",
        display_name="Market",
        governed=True,
        taxonomy_category="regions",
        data_type="dimension",
    )


    update_dimension_governance(
        dimension_name="product",
        display_name="Product",
        governed=True,
        taxonomy_category="products",
        data_type="dimension",
    )


    update_dimension_governance(
        dimension_name="brand",
        display_name="Brand",
        governed=True,
        taxonomy_category="products",
        data_type="dimension",
    )


    update_dimension_governance(
        dimension_name="category",
        display_name="Category",
        governed=True,
        taxonomy_category="products",
        data_type="dimension",
    )


    # -----------------------------------------------------
    # NON-GOVERNED MEASURES / ATTRIBUTES
    # -----------------------------------------------------

    update_dimension_governance(
        dimension_name="revenue",
        display_name="Revenue",
        governed=False,
        data_type="measure",
    )


    update_dimension_governance(
        dimension_name="growth_rate",
        display_name="Growth Rate",
        governed=False,
        data_type="measure",
    )


    update_dimension_governance(
        dimension_name="reporting_period",
        display_name="Reporting Period",
        governed=False,
        data_type="period",
    )


    update_dimension_governance(
        dimension_name="currency",
        display_name="Currency",
        governed=False,
        data_type="dimension",
    )


    update_dimension_governance(
        dimension_name="organisation",
        display_name="Organisation",
        governed=False,
        data_type="dimension",
    )


    update_dimension_governance(
        dimension_name="outlook",
        display_name="Outlook",
        governed=False,
        data_type="text",
    )


    print(
        "Dimension governance seeded."
    )


if __name__ == "__main__":
    seed()