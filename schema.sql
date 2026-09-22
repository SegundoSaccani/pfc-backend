CREATE TABLE "Especie_Pescado"(
    "id" BIGINT NOT NULL,
    "nombre_especie" VARCHAR(255) NOT NULL
);
ALTER TABLE
    "Especie_Pescado" ADD PRIMARY KEY("id");
ALTER TABLE
    "Especie_Pescado" ADD CONSTRAINT "especie_pescado_nombre_especie_unique" UNIQUE("nombre_especie");
CREATE TABLE "Pescador"(
    "id" BIGINT NOT NULL,
    "nro_pescador" BIGINT NOT NULL
);
ALTER TABLE
    "Pescador" ADD PRIMARY KEY("id");
ALTER TABLE
    "Pescador" ADD CONSTRAINT "pescador_nro_pescador_unique" UNIQUE("nro_pescador");
CREATE TABLE "Pescado_individuo"(
    "id" BIGINT NOT NULL,
    "talla" FLOAT(53) NOT NULL,
    "confianza_especie" FLOAT(53) NULL,
    "id_relevamiento" BIGINT NOT NULL,
    "id_especie" BIGINT NOT NULL
);
ALTER TABLE
    "Pescado_individuo" ADD PRIMARY KEY("id");
CREATE TABLE "Relevamiento"(
    "id" BIGINT NOT NULL,
    "fecha_hora" TIMESTAMP(0) WITH
        TIME zone NOT NULL,
        "id_punto_desembarco" BIGINT NULL,
        "ubicacion" geography NULL,
        "id_pescador" BIGINT NOT NULL,
        "id_fiscalizador" BIGINT NOT NULL,
        "observaciones" VARCHAR(255) NULL
);
ALTER TABLE
    "Relevamiento" ADD CONSTRAINT "relevamiento_fecha_hora_id_pescador_id_fiscalizador_unique" UNIQUE(
        "fecha_hora",
        "id_pescador",
        "id_fiscalizador"
    );
ALTER TABLE
    "Relevamiento" ADD PRIMARY KEY("id");
CREATE TABLE "Reglamentacion"(
    "id" BIGINT NOT NULL,
    "fechaInicio" DATE NOT NULL,
    "fechaFin" DATE NULL
);
ALTER TABLE
    "Reglamentacion" ADD PRIMARY KEY("id");
CREATE TABLE "Regla"(
    "id" BIGINT NOT NULL,
    "en_veda" BOOLEAN NOT NULL,
    "talla_min" FLOAT(53) NOT NULL,
    "talla_max" FLOAT(53) NOT NULL,
    "id_reglamentacion" BIGINT NOT NULL,
    "id_especie" BIGINT NOT NULL
);
ALTER TABLE
    "Regla" ADD CONSTRAINT "regla_id_reglamentacion_id_especie_unique" UNIQUE("id_reglamentacion", "id_especie");
ALTER TABLE
    "Regla" ADD PRIMARY KEY("id");
CREATE TABLE "Fiscalizador"(
    "id" BIGINT NOT NULL,
    "nombre_user" VARCHAR(255) NOT NULL
);
ALTER TABLE
    "Fiscalizador" ADD PRIMARY KEY("id");
ALTER TABLE
    "Fiscalizador" ADD CONSTRAINT "fiscalizador_nombre_user_unique" UNIQUE("nombre_user");
CREATE TABLE "Punto_desembarco"(
    "id" BIGINT NOT NULL,
    "nombre" VARCHAR(255) NOT NULL,
    "nro_identificacion" BIGINT NOT NULL
);
ALTER TABLE
    "Punto_desembarco" ADD PRIMARY KEY("id");
ALTER TABLE
    "Punto_desembarco" ADD CONSTRAINT "punto_desembarco_nombre_unique" UNIQUE("nombre");
ALTER TABLE
    "Relevamiento" ADD CONSTRAINT "relevamiento_id_fiscalizador_foreign" FOREIGN KEY("id_fiscalizador") REFERENCES "Fiscalizador"("id");
ALTER TABLE
    "Regla" ADD CONSTRAINT "regla_id_especie_foreign" FOREIGN KEY("id_especie") REFERENCES "Especie_Pescado"("id");
ALTER TABLE
    "Relevamiento" ADD CONSTRAINT "relevamiento_id_punto_desembarco_foreign" FOREIGN KEY("id_punto_desembarco") REFERENCES "Punto_desembarco"("id");
ALTER TABLE
    "Regla" ADD CONSTRAINT "regla_id_reglamentacion_foreign" FOREIGN KEY("id_reglamentacion") REFERENCES "Reglamentacion"("id");
ALTER TABLE
    "Relevamiento" ADD CONSTRAINT "relevamiento_id_pescador_foreign" FOREIGN KEY("id_pescador") REFERENCES "Pescador"("id");
ALTER TABLE
    "Pescado_individuo" ADD CONSTRAINT "pescado_individuo_id_relevamiento_foreign" FOREIGN KEY("id_relevamiento") REFERENCES "Relevamiento"("id");
ALTER TABLE
    "Pescado_individuo" ADD CONSTRAINT "pescado_individuo_id_especie_foreign" FOREIGN KEY("id_especie") REFERENCES "Especie_Pescado"("id");