from src.database import (
    add_term,
    create_concept,
    initialize_database,
    update_dimension_governance,
)


def seed_product_taxonomy():
    """
    Create a small multilingual product taxonomy.
    """

    # =====================================================
    # PREMIUM COFFEE
    # =====================================================

    premium_coffee_id = create_concept(
        category="products",
        display_label="Premium Coffee",
        description=(
            "Premium coffee product concept."
        ),
    )


    product_terms = [
        (
            "Premium Coffee",
            "en",
            "preferred",
        ),
        (
            "Premium Kaffee",
            "de",
            "preferred",
        ),
        (
            "Café Premium",
            "es",
            "preferred",
        ),
        (
            "Café Premium",
            "fr",
            "preferred",
        ),
        (
            "Caffè Premium",
            "it",
            "preferred",
        ),
        (
            "Premium Koffie",
            "nl",
            "preferred",
        ),
        (
            "プレミアムコーヒー",
            "ja",
            "preferred",
        ),
    ]


    for (
        term,
        language_code,
        term_type,
    ) in product_terms:

        add_term(
            concept_id=premium_coffee_id,
            term=term,
            language_code=language_code,
            term_type=term_type,
            source="mvp_seed",
        )


    # =====================================================
    # STANDARD COFFEE
    # =====================================================

    standard_coffee_id = create_concept(
        category="products",
        display_label="Standard Coffee",
        description=(
            "Standard coffee product concept."
        ),
    )


    standard_terms = [
        (
            "Standard Coffee",
            "en",
        ),
        (
            "Standard Kaffee",
            "de",
        ),
        (
            "Café Estándar",
            "es",
        ),
        (
            "Café Standard",
            "fr",
        ),
    ]


    for (
        term,
        language_code,
    ) in standard_terms:

        add_term(
            concept_id=standard_coffee_id,
            term=term,
            language_code=language_code,
            term_type="preferred",
            source="mvp_seed",
        )


    # =====================================================
    # PREMIUM TEA
    # =====================================================

    premium_tea_id = create_concept(
        category="products",
        display_label="Premium Tea",
        description=(
            "Premium tea product concept."
        ),
    )


    tea_terms = [
        (
            "Premium Tea",
            "en",
        ),
        (
            "Premium Tee",
            "de",
        ),
        (
            "Té Premium",
            "es",
        ),
        (
            "Thé Premium",
            "fr",
        ),
        (
            "プレミアムティー",
            "ja",
        ),
    ]


    for (
        term,
        language_code,
    ) in tea_terms:

        add_term(
            concept_id=premium_tea_id,
            term=term,
            language_code=language_code,
            term_type="preferred",
            source="mvp_seed",
        )


def seed_region_taxonomy():
    """
    Create a small multilingual region/country taxonomy.
    """

    # =====================================================
    # GERMANY
    # =====================================================

    germany_id = create_concept(
        category="regions",
        display_label="Germany",
        description=(
            "Country concept for Germany."
        ),
    )


    germany_terms = [
        (
            "Germany",
            "en",
        ),
        (
            "Deutschland",
            "de",
        ),
        (
            "Alemania",
            "es",
        ),
        (
            "Allemagne",
            "fr",
        ),
        (
            "ドイツ",
            "ja",
        ),
    ]


    for (
        term,
        language_code,
    ) in germany_terms:

        add_term(
            concept_id=germany_id,
            term=term,
            language_code=language_code,
            term_type="preferred",
            source="mvp_seed",
        )


    # =====================================================
    # SPAIN
    # =====================================================

    spain_id = create_concept(
        category="regions",
        display_label="Spain",
        description=(
            "Country concept for Spain."
        ),
    )


    spain_terms = [
        (
            "Spain",
            "en",
        ),
        (
            "España",
            "es",
        ),
        (
            "Spanien",
            "de",
        ),
        (
            "Espagne",
            "fr",
        ),
        (
            "スペイン",
            "ja",
        ),
    ]


    for (
        term,
        language_code,
    ) in spain_terms:

        add_term(
            concept_id=spain_id,
            term=term,
            language_code=language_code,
            term_type="preferred",
            source="mvp_seed",
        )


    # =====================================================
    # FRANCE
    # =====================================================

    france_id = create_concept(
        category="regions",
        display_label="France",
        description=(
            "Country concept for France."
        ),
    )


    france_terms = [
        (
            "France",
            "en",
        ),
        (
            "France",
            "fr",
        ),
        (
            "Frankreich",
            "de",
        ),
        (
            "Francia",
            "es",
        ),
        (
            "フランス",
            "ja",
        ),
    ]


    for (
        term,
        language_code,
    ) in france_terms:

        add_term(
            concept_id=france_id,
            term=term,
            language_code=language_code,
            term_type="preferred",
            source="mvp_seed",
        )


    # =====================================================
    # JAPAN
    # =====================================================

    japan_id = create_concept(
        category="regions",
        display_label="Japan",
        description=(
            "Country concept for Japan."
        ),
    )


    japan_terms = [
        (
            "Japan",
            "en",
        ),
        (
            "日本",
            "ja",
        ),
        (
            "Japón",
            "es",
        ),
        (
            "Japon",
            "fr",
        ),
    ]


    for (
        term,
        language_code,
    ) in japan_terms:

        add_term(
            concept_id=japan_id,
            term=term,
            language_code=language_code,
            term_type="preferred",
            source="mvp_seed",
        )


    # =====================================================
    # UNITED KINGDOM
    # =====================================================

    uk_id = create_concept(
        category="regions",
        display_label="United Kingdom",
        description=(
            "Country concept for the United Kingdom."
        ),
    )


    uk_terms = [
        (
            "United Kingdom",
            "en",
        ),
        (
            "UK",
            "en",
        ),
        (
            "Vereinigtes Königreich",
            "de",
        ),
        (
            "Reino Unido",
            "es",
        ),
        (
            "Royaume-Uni",
            "fr",
        ),
        (
            "イギリス",
            "ja",
        ),
    ]


    for (
        term,
        language_code,
    ) in uk_terms:

        add_term(
            concept_id=uk_id,
            term=term,
            language_code=language_code,
            term_type="preferred",
            source="mvp_seed",
        )


def seed_governance():
    """
    Keep the starting governance deliberately small.

    Product and country are governed.

    Other dimensions discovered by AI remain pending
    so the MVP can demonstrate new-field governance.
    """

    update_dimension_governance(
        dimension_name="product",
        governed=True,
        taxonomy_category="products",
        display_name="Product",
        data_type="dimension",
    )


    update_dimension_governance(
        dimension_name="country",
        governed=True,
        taxonomy_category="regions",
        display_name="Country",
        data_type="dimension",
    )


    update_dimension_governance(
        dimension_name="region",
        governed=True,
        taxonomy_category="regions",
        display_name="Region",
        data_type="dimension",
    )


def seed_database():
    """
    Build the clean MVP starting taxonomy.
    """

    initialize_database()

    seed_product_taxonomy()

    seed_region_taxonomy()

    seed_governance()

    print()
    print(
        "Fresh multilingual MVP taxonomy seeded."
    )

    print()
    print(
        "Governed fields:"
    )

    print(
        "- Product"
    )

    print(
        "- Country"
    )

    print(
        "- Region"
    )

    print()
    print(
        "Other AI-discovered fields will begin "
        "as new/pending fields."
    )


if __name__ == "__main__":
    seed_database()