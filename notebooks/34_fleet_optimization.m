// BI: PowerBI load script for notebook 34_fleet_optimization
// notebooks_folder: https://powerbi.tips/2016/08/using-variables-for-file-locations/

//Schedule
let
    Source = Csv.Document(File.Contents(notebooks_folder &  "activity_logs.csv"),[Delimiter=",", Columns=7, Encoding=1252, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Split Column by Delimiter" = Table.SplitColumn(#"Promoted Headers", "ActivityName", Splitter.SplitTextByDelimiter(":", QuoteStyle.Csv), {"ActivityName.1", "ActivityName.2"}),
    #"Changed Type" = Table.TransformColumnTypes(#"Split Column by Delimiter",{{"trip", Int64.Type}, {"ActivityID", type text}, {"ActivityName.1", type text}, {"ActivityName.2", type text}, {"ActivityClass", type text}, {"TimestampStart", type datetime}, {"TimestampStop", type datetime}, {"TimestampDt", Int64.Type}}),
    #"Renamed Columns" = Table.RenameColumns(#"Changed Type",{{"ActivityName.1", "ActivityType"}, {"ActivityName.2", "ActivityName"}}),
    #"Removed Columns" = Table.RemoveColumns(#"Renamed Columns",{"ActivityType", "ActivityName"}),
    #"Added Custom" = Table.AddColumn(#"Removed Columns", "Custom", each [ActivityID]&":"& Number.ToText([trip])),
    #"Renamed Columns1" = Table.RenameColumns(#"Added Custom",{{"Custom", "uuid"}}),
    #"Reordered Columns" = Table.ReorderColumns(#"Renamed Columns1",{"uuid", "trip", "ActivityID", "ActivityClass", "TimestampStart", "TimestampStop", "TimestampDt"})
in
    #"Reordered Columns"
	
//Planning
let
    Source = Csv.Document(File.Contents(notebooks_folder &  "activities.csv"),[Delimiter=",", Columns=14, Encoding=1252, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Split Column by Delimiter" = Table.SplitColumn(#"Promoted Headers", "ActivityName", Splitter.SplitTextByDelimiter(":", QuoteStyle.Csv), {"ActivityName.1", "ActivityName.2"}),
    #"Changed Type" = Table.TransformColumnTypes(#"Split Column by Delimiter",{{"ActivityID", type text}, {"ActivityName.1", type text}, {"ActivityName.2", type text}, {"ActivityClass", type text}, {"ParentId", type text}, {"ParentName", type text}, {"ParentLevel", Int64.Type}, {"OriginID", type text}, {"OriginName", type text}, {"DestinationID", type text}, {"DestinationName", type text}, {"ProcessorID", type text}, {"ProcessorName", type text}, {"MoverID", type text}, {"MoverName", type text}}),
    #"Renamed Columns" = Table.RenameColumns(#"Changed Type",{{"ActivityName.1", "ActivityType"}, {"ActivityName.2", "ActivityName"}}),
    #"Added Custom" = Table.AddColumn(#"Renamed Columns", "Custom", each [ProcessorName] & " " & [MoverName] & " " & [DestinationName]),
    #"Renamed Columns1" = Table.RenameColumns(#"Added Custom",{{"Custom", "ResourceSetName"}}),
    #"Filtered Rows" = Table.SelectRows(#"Renamed Columns1", each ([ActivityType] <> "sequential_activity_subcycle" and [ActivityType] <> "while_sequential_activity_subcycle"))
in
    #"Filtered Rows"
	
//Vessels
let
    Source = Csv.Document(File.Contents(notebooks_folder &  "concepts.csv"),[Delimiter=",", Columns=3, Encoding=1252, QuoteStyle=QuoteStyle.None]),
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"Column1", type text}, {"Column2", type text}, {"Column3", type text}}),
    #"Promoted Headers" = Table.PromoteHeaders(#"Changed Type", [PromoteAllScalars=true]),
    #"Changed Type1" = Table.TransformColumnTypes(#"Promoted Headers",{{"ConceptName", type text}, {"ConceptID", type text}, {"ConceptClass", type text}}),
    #"Filtered Rows" = Table.SelectRows(#"Changed Type1", each ([ConceptClass] = "TransportProcessingResource")),
    #"Renamed Columns" = Table.RenameColumns(#"Filtered Rows",{{"ConceptName", "VesselName"}, {"ConceptID", "ConceptID"}, {"ConceptClass", "VesselClass"}})
in
    #"Renamed Columns"

//Sites
let
    Source = Csv.Document(File.Contents(notebooks_folder &  "concepts.csv"),[Delimiter=",", Columns=3, Encoding=1252, QuoteStyle=QuoteStyle.None]),
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"Column1", type text}, {"Column2", type text}, {"Column3", type text}}),
    #"Promoted Headers" = Table.PromoteHeaders(#"Changed Type", [PromoteAllScalars=true]),
    #"Changed Type1" = Table.TransformColumnTypes(#"Promoted Headers",{{"ConceptName", type text}, {"ConceptID", type text}, {"ConceptClass", type text}}),
    #"Filtered Rows" = Table.SelectRows(#"Changed Type1", each ([ConceptClass] = "Site")),
    #"Renamed Columns" = Table.RenameColumns(#"Filtered Rows",{{"ConceptClass", "SiteClass"}, {"ConceptName", "SiteName"}})
in
    #"Renamed Columns"

//Campaigns
let
    Source = Csv.Document(File.Contents(notebooks_folder &  "resources.csv"),[Delimiter=",", Columns=6, Encoding=1252, QuoteStyle=QuoteStyle.None]),
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"Column1", type text}, {"Column2", type text}, {"Column3", type text}, {"Column4", type text}, {"Column5", type text}, {"Column6", type text}}),
    #"Promoted Headers" = Table.PromoteHeaders(#"Changed Type", [PromoteAllScalars=true]),
    #"Changed Type1" = Table.TransformColumnTypes(#"Promoted Headers",{{"ActivityID", type text}, {"ActivityName", type text}, {"ActivityClass", type text}, {"ConceptID", type text}, {"ConceptName", type text}, {"ConceptMode", type text}}),
    #"Merged Queries" = Table.NestedJoin(#"Changed Type1", {"ConceptID"}, Vessels, {"ConceptID"}, "Vessels", JoinKind.LeftOuter),
    #"Expanded Vessels" = Table.ExpandTableColumn(#"Merged Queries", "Vessels", {"VesselName", "VesselClass"}, {"Vessels.VesselName", "Vessels.VesselClass"})
in
    #"Expanded Vessels"

//Activities (alas, we cannot code colors in load script)
let
    Query1 = #table(
 type table
    [
        #"Number Column"=number, 
        #"Text Column"=text
    ], 
 {
  {1,"sailing full"},
  {2,"sailing empty"},
  {3,"loading"},
  {4,"unloading"}  
 }
),
    #"Renamed Columns" = Table.RenameColumns(Query1,{{"Text Column", "ActivityType"}})
in
    #"Renamed Columns"	