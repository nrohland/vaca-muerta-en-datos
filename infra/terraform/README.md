# Adopción optativa de datasets existentes

**Facturación deshabilitada.** Este módulo no crea runtime, buckets, red, WIF, cuentas de servicio, APIs ni vinculaciones de facturación. No contiene credenciales. Default `adopt_existing_datasets=false`: cero datasets administrados. El estado usa backend local; respaldarlo fuera de Git y evitar ejecuciones concurrentes desde otras máquinas.

La configuración sólo permite adoptar los cuatro datasets candidatos existentes del proyecto `vaca-muerta-pulse`, región `US`. Nunca ejecutar apply para recrear lo que ya existe. `prevent_destroy` y `ignore_changes` protegen la primera adopción de expiraciones, ACLs y metadatos; no certifican que las cuotas o políticas remotas sean correctas.

```sh
terraform init
terraform fmt -check
terraform validate
# Autenticar ADC con la identidad autorizada, fuera del repo.
# Una vez verificados los cuatro datasets existentes:
terraform import -var='adopt_existing_datasets=true' 'google_bigquery_dataset.candidate["raw_cap4_candidate_dev"]' 'projects/vaca-muerta-pulse/datasets/raw_cap4_candidate_dev'
terraform import -var='adopt_existing_datasets=true' 'google_bigquery_dataset.candidate["stg_cap4_candidate_dev"]' 'projects/vaca-muerta-pulse/datasets/stg_cap4_candidate_dev'
terraform import -var='adopt_existing_datasets=true' 'google_bigquery_dataset.candidate["int_cap4_candidate_dev"]' 'projects/vaca-muerta-pulse/datasets/int_cap4_candidate_dev'
terraform import -var='adopt_existing_datasets=true' 'google_bigquery_dataset.candidate["marts_cap4_candidate_dev"]' 'projects/vaca-muerta-pulse/datasets/marts_cap4_candidate_dev'
terraform plan -var='adopt_existing_datasets=true' -out=adoption.tfplan
```

Los imports escriben estado local y leen GCP; no se ejecutaron en esta entrega. Revisar plan: la adopción inicial debería quedar sin cambios remotos; cualquier create/update/destroy exige investigar antes de continuar. Tras adoptar, conservar `adopt_existing_datasets=true` en configuración local para planes posteriores; cambiarlo a false propone retirar recursos y prevent_destroy debe bloquearlo. El archivo .terraform.lock.hcl fija la versión del provider; versionarlo. El módulo no habilita APIs para resolver errores de acceso.
