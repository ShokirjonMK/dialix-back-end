-- Why ? you may ask. Tortoise orm ins postgres uses timestamps with timezone support. If your table did not specefied this, this function alters every column in current database
-- It only changes the data type. So be careful
do
$$
declare
    rec record;
begin
    for rec in
        select table_name
        from information_schema.columns
        where column_name in ('created_at', 'updated_at', 'deleted_at')
          and table_schema = 'public'
    loop
        -- alter 'created_at'
        if exists (
            select 1
            from information_schema.columns
            where table_name = rec.table_name and column_name = 'created_at'
        ) then
            execute format('alter table %I alter column created_at set data type timestamp with time zone, alter column created_at set default current_timestamp', rec.table_name);
        end if;

        -- alter 'updated_at'
        if exists (
            select 1
            from information_schema.columns
            where table_name = rec.table_name and column_name = 'updated_at'
        ) then
            execute format('alter table %I alter column updated_at set data type timestamp with time zone, alter column updated_at set default current_timestamp', rec.table_name);
        end if;

        -- alter 'deleted_at'
        if exists (
            select 1
            from information_schema.columns
            where table_name = rec.table_name and column_name = 'deleted_at'
        ) then
            execute format('alter table %I alter column deleted_at set data type timestamp with time zone, alter column deleted_at set default current_timestamp', rec.table_name);
        end if;        
    end loop;
end
$$;
