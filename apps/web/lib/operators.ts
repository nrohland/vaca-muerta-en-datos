// Preserve declared legal punctuation; PLUSPETROL represents two legal entities.
export const operatorName=(id:string,declared:string)=>id==='PLUSPETROL'
 ?'PLUSPETROL (GRUPO)'
 :declared.trim().replace(/\s+/g,' ').toLocaleUpperCase('es-AR');
