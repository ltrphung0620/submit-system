/*
Fresh-database baseline for Submit System.

Source migration head: 20260727_0006
Target database: submission

This script is intentionally fail-closed:
- it switches explicitly to "submission" and verifies the active database;
- it stops if any Submit System table already exists;
- all schema and seed changes run in one transaction.
*/

USE [submission];
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;

IF DB_NAME() <> N'submission'
BEGIN
    ;THROW 51000, 'Wrong target database after USE submission. Operation stopped.', 1;
END;

IF EXISTS (
    SELECT 1
    FROM sys.tables
    WHERE [schema_id] = SCHEMA_ID(N'dbo')
      AND [name] IN (
          N'alembic_version',
          N'query_sets',
          N'queries',
          N'result_candidates',
          N'image_attachments',
          N'audit_logs',
          N'export_snapshots'
      )
)
BEGIN
    ;THROW 51001, 'Submit System tables already exist. No changes were applied.', 1;
END;

BEGIN TRY
    BEGIN TRANSACTION;

    CREATE TABLE [dbo].[query_sets] (
        [id] VARCHAR(36) NOT NULL,
        [name] NVARCHAR(255) NOT NULL,
        [original_zip_name] NVARCHAR(255) NOT NULL,
        [is_active] BIT NOT NULL,
        [created_at] DATETIMEOFFSET NOT NULL,
        [created_by] NVARCHAR(255) NOT NULL,
        [import_status] VARCHAR(32) NOT NULL,
        CONSTRAINT [pk_query_sets] PRIMARY KEY ([id])
    );

    CREATE INDEX [ix_query_sets_is_active]
        ON [dbo].[query_sets] ([is_active]);

    CREATE TABLE [dbo].[queries] (
        [id] VARCHAR(36) NOT NULL,
        [query_set_id] VARCHAR(36) NOT NULL,
        [file_name] NVARCHAR(255) NOT NULL,
        [file_name_key] NVARCHAR(255) NOT NULL,
        [query_type] VARCHAR(16) NOT NULL,
        [content] NVARCHAR(MAX) NOT NULL,
        [display_order] INT NOT NULL,
        [source_path] NVARCHAR(1024) NOT NULL,
        [next_arrival_seq] INT NOT NULL,
        [created_at] DATETIMEOFFSET NOT NULL,
        CONSTRAINT [pk_queries] PRIMARY KEY ([id]),
        CONSTRAINT [fk_queries_query_set_id_query_sets]
            FOREIGN KEY ([query_set_id])
            REFERENCES [dbo].[query_sets] ([id])
            ON DELETE CASCADE,
        CONSTRAINT [uq_query_file_name_key] UNIQUE ([file_name_key])
    );

    CREATE INDEX [ix_queries_query_type]
        ON [dbo].[queries] ([query_type]);

    CREATE INDEX [ix_queries_set_type]
        ON [dbo].[queries] ([query_set_id], [query_type]);

    CREATE TABLE [dbo].[result_candidates] (
        [id] VARCHAR(36) NOT NULL,
        [query_id] VARCHAR(36) NOT NULL,
        [arrival_seq] INT NOT NULL,
        [priority] INT NOT NULL,
        [video_id] NVARCHAR(255) NOT NULL,
        [frame_ids] NVARCHAR(MAX) NOT NULL,
        [answer] NVARCHAR(MAX) NULL,
        [submitter] NVARCHAR(255) NOT NULL,
        [note] NVARCHAR(MAX) NULL,
        [created_at] DATETIMEOFFSET NOT NULL,
        [updated_at] DATETIMEOFFSET NOT NULL,
        [deleted_at] DATETIMEOFFSET NULL,
        [deleted_by] NVARCHAR(255) NULL,
        [version] INT NOT NULL,
        [structural_validation_status] VARCHAR(32) NOT NULL,
        [official_validation_status] VARCHAR(32) NOT NULL,
        CONSTRAINT [pk_result_candidates] PRIMARY KEY ([id]),
        CONSTRAINT [fk_result_candidates_query_id_queries]
            FOREIGN KEY ([query_id])
            REFERENCES [dbo].[queries] ([id])
            ON DELETE CASCADE,
        CONSTRAINT [uq_query_arrival_seq]
            UNIQUE ([query_id], [arrival_seq])
    );

    CREATE INDEX [ix_results_query_deleted]
        ON [dbo].[result_candidates] ([query_id], [deleted_at]);

    CREATE INDEX [ix_result_candidates_submitter]
        ON [dbo].[result_candidates] ([submitter]);

    CREATE INDEX [ix_results_submitter_created]
        ON [dbo].[result_candidates] ([submitter], [created_at]);

    CREATE UNIQUE INDEX [ux_active_query_priority]
        ON [dbo].[result_candidates] ([query_id], [priority])
        WHERE [deleted_at] IS NULL;

    CREATE TABLE [dbo].[image_attachments] (
        [id] VARCHAR(36) NOT NULL,
        [result_candidate_id] VARCHAR(36) NOT NULL,
        [original_mime_type] VARCHAR(100) NULL,
        [detected_mime_type] VARCHAR(100) NOT NULL,
        [storage_key] VARCHAR(512) NOT NULL,
        [byte_size] INT NOT NULL,
        [sha256] VARCHAR(64) NOT NULL,
        [created_at] DATETIMEOFFSET NOT NULL,
        CONSTRAINT [pk_image_attachments] PRIMARY KEY ([id]),
        CONSTRAINT [fk_image_attachments_result_candidate_id_result_candidates]
            FOREIGN KEY ([result_candidate_id])
            REFERENCES [dbo].[result_candidates] ([id])
            ON DELETE CASCADE,
        CONSTRAINT [uq_image_attachments_result_candidate_id]
            UNIQUE ([result_candidate_id]),
        CONSTRAINT [uq_image_attachments_storage_key]
            UNIQUE ([storage_key])
    );

    CREATE INDEX [ix_image_attachments_sha256]
        ON [dbo].[image_attachments] ([sha256]);

    CREATE TABLE [dbo].[audit_logs] (
        [id] VARCHAR(36) NOT NULL,
        [action] VARCHAR(32) NOT NULL,
        [entity_type] VARCHAR(64) NOT NULL,
        [entity_id] VARCHAR(36) NOT NULL,
        [actor] NVARCHAR(255) NOT NULL,
        [old_value] NVARCHAR(MAX) NULL,
        [new_value] NVARCHAR(MAX) NULL,
        [created_at] DATETIMEOFFSET NOT NULL,
        CONSTRAINT [pk_audit_logs] PRIMARY KEY ([id])
    );

    CREATE INDEX [ix_audit_entity]
        ON [dbo].[audit_logs] ([entity_type], [entity_id]);

    CREATE TABLE [dbo].[export_snapshots] (
        [id] VARCHAR(36) NOT NULL,
        [query_set_id] VARCHAR(36) NOT NULL,
        [status] VARCHAR(32) NOT NULL,
        [format_verification_status] VARCHAR(32) NOT NULL,
        [created_at] DATETIMEOFFSET NOT NULL,
        [archive_path] VARCHAR(512) NOT NULL,
        [validation_report] NVARCHAR(MAX) NOT NULL,
        [source_data_version] VARCHAR(64) NOT NULL,
        CONSTRAINT [pk_export_snapshots] PRIMARY KEY ([id]),
        CONSTRAINT [fk_export_snapshots_query_set_id_query_sets]
            FOREIGN KEY ([query_set_id])
            REFERENCES [dbo].[query_sets] ([id])
    );

    CREATE INDEX [ix_exports_query_set_created]
        ON [dbo].[export_snapshots] ([query_set_id], [created_at]);

    INSERT INTO [dbo].[query_sets] (
        [id],
        [name],
        [original_zip_name],
        [is_active],
        [created_at],
        [created_by],
        [import_status]
    )
    VALUES (
        '00000000-0000-0000-0000-000000000001',
        N'API submissions',
        N'api-submissions',
        1,
        TODATETIMEOFFSET(SYSUTCDATETIME(), '+00:00'),
        N'system',
        'complete'
    );

    CREATE TABLE [dbo].[alembic_version] (
        [version_num] VARCHAR(32) NOT NULL,
        CONSTRAINT [alembic_version_pkc] PRIMARY KEY ([version_num])
    );

    INSERT INTO [dbo].[alembic_version] ([version_num])
    VALUES ('20260727_0006');

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH;

SELECT
    [version_num] AS [schema_revision]
FROM [dbo].[alembic_version];
